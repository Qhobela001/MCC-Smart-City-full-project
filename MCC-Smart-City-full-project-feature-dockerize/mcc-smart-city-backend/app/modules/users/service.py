from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.modules.departments.models import Department
from app.modules.roles.models import Role
from app.modules.users.models import User


def ensure_unique(
    db: Session,
    email: str | None,
    employee_number: str | None = None,
    phone_number: str | None = None,
    exclude_user_id: int | None = None,
) -> None:
    checks = (
        ("email", email.lower().strip() if email else None),
        (
            "employee_number",
            employee_number.strip() if employee_number else None,
        ),
        (
            "phone_number",
            phone_number.strip() if phone_number else None,
        ),
    )

    for field_name, value in checks:
        if not value:
            continue

        existing_user = db.scalar(
            select(User).where(getattr(User, field_name) == value)
        )

        if (
            existing_user is not None
            and existing_user.id != exclude_user_id
        ):
            readable_name = field_name.replace("_", " ").title()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{readable_name} already exists",
            )


def protect_superadmin_target(
    actor: User,
    target: User,
) -> None:
    if target.is_superuser and not actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SuperAdmin accounts are protected.",
        )


def prevent_self_deactivation(
    actor: User,
    target: User,
    new_is_active: bool | None,
) -> None:
    if (
        actor.id == target.id
        and new_is_active is False
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )


def validate_department(
    db: Session,
    department_id: int | None,
    *,
    required: bool,
) -> Department | None:
    if department_id is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A department is required.",
            )
        return None

    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    if not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected department is inactive.",
        )

    return department


def validate_role_assignment(
    db: Session,
    actor: User,
    role_id: int | None,
    *,
    required: bool,
) -> Role | None:
    if role_id is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A role is required.",
            )
        return None

    role = db.get(Role, role_id)

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    if not role.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected role is inactive.",
        )

    is_superadmin_role = (
        role.is_system
        or role.name.strip().lower() == "superadmin"
    )

    if is_superadmin_role and not actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a SuperAdmin can assign a protected system role.",
        )

    return role


def validate_create_access(
    db: Session,
    actor: User,
    *,
    is_superuser: bool,
    department_id: int | None,
    role_id: int | None,
) -> None:
    if is_superuser and not actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a SuperAdmin can create another SuperAdmin.",
        )

    validate_department(
        db,
        department_id,
        required=not is_superuser,
    )
    validate_role_assignment(
        db,
        actor,
        role_id,
        required=not is_superuser,
    )


def validate_update_access(
    db: Session,
    actor: User,
    target: User,
    update_data: dict,
) -> None:
    protect_superadmin_target(actor, target)

    prevent_self_deactivation(
        actor,
        target,
        update_data.get("is_active"),
    )

    if "department_id" in update_data:
        validate_department(
            db,
            update_data["department_id"],
            required=not target.is_superuser,
        )

    if "role_id" in update_data:
        validate_role_assignment(
            db,
            actor,
            update_data["role_id"],
            required=not target.is_superuser,
        )


def change_password(
    db: Session,
    user: User,
    current_password: str,
    new_password: str,
) -> User:
    if not verify_password(
        current_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must contain at least 8 characters.",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The new password must be different from the current password.",
        )

    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False

    db.commit()
    db.refresh(user)
    return user


def reset_password(
    db: Session,
    actor: User,
    target: User,
    new_temporary_password: str,
) -> User:
    protect_superadmin_target(actor, target)

    if actor.id == target.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Use the change-password endpoint to change "
                "your own password."
            ),
        )

    if len(new_temporary_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "The temporary password must contain at least "
                "8 characters."
            ),
        )

    target.hashed_password = get_password_hash(
        new_temporary_password
    )
    target.must_change_password = True

    db.commit()
    db.refresh(target)
    return target
