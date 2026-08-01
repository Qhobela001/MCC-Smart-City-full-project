from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (
    get_current_user,
    get_db,
    require_permission,
)
from app.core.security import get_password_hash
from app.modules.users import repository, service
from app.modules.users.models import User
from app.modules.users.schemas import (
    PasswordChange,
    PasswordResetByAdmin,
    UserCreate,
    UserRead,
    UserUpdate,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


@router.get(
    "",
    response_model=list[UserRead],
)
def list_users(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users.view")),
) -> list[User]:
    """
    SuperAdmin:
        Returns every user, including protected SuperAdmin accounts.

    Authorised non-SuperAdmin support staff:
        Returns all ordinary MCC users across all departments.
        SuperAdmin accounts are excluded from the result.
    """
    return repository.list_visible_to(db, actor)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users.create")),
) -> User:
    service.validate_create_access(
        db,
        actor,
        is_superuser=payload.is_superuser,
        department_id=payload.department_id,
        role_id=payload.role_id,
    )

    service.ensure_unique(
        db,
        payload.email,
        payload.employee_number,
        payload.phone_number,
    )

    data = payload.model_dump(
        exclude={"temporary_password"}
    )
    data["full_name"] = data["full_name"].strip()
    data["email"] = data["email"].strip().lower()

    if data.get("employee_number"):
        data["employee_number"] = (
            data["employee_number"].strip()
        )

    if data.get("phone_number"):
        data["phone_number"] = (
            data["phone_number"].strip()
        )

    data["hashed_password"] = get_password_hash(
        payload.temporary_password
    )

    user = User(
        **data,
        must_change_password=True,
        is_active=True,
    )
    return repository.create(db, user)


@router.post(
    "/change-password",
    response_model=UserRead,
)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    return service.change_password(
        db,
        current_user,
        payload.current_password,
        payload.new_password,
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users.view")),
) -> User:
    user = repository.get_visible_to(
        db,
        actor,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users.update")),
) -> User:
    user = repository.get_visible_to(
        db,
        actor,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    update_data = payload.model_dump(
        exclude_unset=True
    )

    service.validate_update_access(
        db,
        actor,
        user,
        update_data,
    )

    email = update_data.get("email", user.email)
    employee_number = update_data.get(
        "employee_number",
        user.employee_number,
    )
    phone_number = update_data.get(
        "phone_number",
        user.phone_number,
    )

    service.ensure_unique(
        db,
        email,
        employee_number,
        phone_number,
        exclude_user_id=user.id,
    )

    for field_name, value in update_data.items():
        if field_name == "email" and value:
            value = value.strip().lower()
        elif (
            field_name
            in {"full_name", "employee_number", "phone_number"}
            and isinstance(value, str)
        ):
            value = value.strip()

        setattr(user, field_name, value)

    return repository.save(db, user)


@router.post(
    "/{user_id}/reset-password",
    response_model=UserRead,
)
def reset_user_password(
    user_id: int,
    payload: PasswordResetByAdmin,
    db: Session = Depends(get_db),
    actor: User = Depends(
        require_permission("users.reset_password")
    ),
) -> User:
    user = repository.get_visible_to(
        db,
        actor,
        user_id,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return service.reset_password(
        db,
        actor,
        user,
        payload.new_temporary_password,
    )
