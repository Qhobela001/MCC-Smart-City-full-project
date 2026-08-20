import logging
from urllib.parse import quote

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_password_reset_token,
    decode_password_reset_token,
    get_password_hash,
    password_reset_token_matches_hash,
    verify_password,
)
from app.modules.authentication.email_service import (
    send_password_reset_email,
)
from app.modules.authentication.repository import (
    find_by_email,
    find_by_id,
    find_by_identifier,
)
from app.modules.users.models import UserStatus


logger = logging.getLogger(__name__)

FORGOT_PASSWORD_MESSAGE = (
    "If an active account exists for that email address, "
    "password reset instructions have been sent."
)

RESET_SUCCESS_MESSAGE = (
    "Your password has been reset successfully. "
    "You can now sign in with your new password."
)


def authenticate(
    db: Session,
    identifier: str,
    password: str,
):
    user = find_by_identifier(
        db,
        identifier,
    )

    if not user or not verify_password(
        password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid login credentials",
        )

    if (
        not user.is_active
        or user.status != UserStatus.active
    ):
        raise HTTPException(
            status_code=403,
            detail="User account is not active",
        )

    return (
        create_access_token(
            {
                "sub": str(user.id),
                "user_id": user.id,
            }
        ),
        user,
    )


def request_password_reset(
    db: Session,
    email: str,
) -> str:
    user = find_by_email(
        db,
        email,
    )

    if (
        user is None
        or not user.is_active
        or user.status != UserStatus.active
    ):
        return FORGOT_PASSWORD_MESSAGE

    token = create_password_reset_token(
        user_id=user.id,
        email=user.email,
        hashed_password=user.hashed_password,
    )

    reset_url = (
        settings.PASSWORD_RESET_FRONTEND_URL.rstrip("/")
        + "/reset-password?token="
        + quote(token, safe="")
    )

    sent = send_password_reset_email(
        recipient=user.email,
        recipient_name=user.full_name,
        reset_url=reset_url,
    )

    if not sent:
        logger.info(
            "Password reset request accepted for user id %s",
            user.id,
        )

    return FORGOT_PASSWORD_MESSAGE


def reset_password(
    db: Session,
    token: str,
    new_password: str,
) -> str:
    payload = decode_password_reset_token(token)

    if payload is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "This password reset link is invalid or has expired. "
                "Request a new one."
            ),
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="Invalid password reset link",
        )

    user = find_by_id(
        db,
        user_id,
    )

    if (
        user is None
        or not user.is_active
        or user.status != UserStatus.active
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid password reset link",
        )

    if user.email.lower() != str(payload["email"]).lower():
        raise HTTPException(
            status_code=400,
            detail="Invalid password reset link",
        )

    if not password_reset_token_matches_hash(
        str(payload["pwd"]),
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "This password reset link has already been used "
                "or is no longer valid."
            ),
        )

    if verify_password(
        new_password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Your new password must be different from your current password"
            ),
        )

    user.hashed_password = get_password_hash(
        new_password
    )
    user.must_change_password = False

    db.add(user)
    db.commit()
    db.refresh(user)

    return RESET_SUCCESS_MESSAGE
