from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.authentication.schemas import (
    AuthMessageResponse,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
)
from app.modules.authentication.service import (
    authenticate,
    request_password_reset,
    reset_password,
)
from app.modules.users.schemas import UserRead


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    token, user = authenticate(
        db,
        payload.identifier,
        payload.password,
    )

    return LoginResponse(
        access_token=token,
        user=user,
    )


@router.post(
    "/forgot-password",
    response_model=AuthMessageResponse,
)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    return AuthMessageResponse(
        message=request_password_reset(
            db,
            payload.email,
        )
    )


@router.post(
    "/reset-password",
    response_model=AuthMessageResponse,
)
def complete_password_reset(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return AuthMessageResponse(
        message=reset_password(
            db,
            payload.token,
            payload.new_password,
        )
    )


@router.get(
    "/me",
    response_model=UserRead,
)
def me(
    user=Depends(get_current_user),
):
    return user
