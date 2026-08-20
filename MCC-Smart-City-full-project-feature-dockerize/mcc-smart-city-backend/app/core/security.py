import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    if not plain_password or not hashed_password:
        return False

    try:
        return password_hash.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    payload = data.copy()

    user_id = payload.get("user_id") or payload.get("sub")

    if user_id is not None:
        payload["sub"] = str(user_id)

    payload.update(
        {
            "exp": datetime.now(timezone.utc)
            + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            ),
            "type": "access",
        }
    )

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != "access":
            return None

        return payload

    except JWTError:
        return None


def _password_fingerprint(hashed_password: str) -> str:
    return hashlib.sha256(
        hashed_password.encode("utf-8")
    ).hexdigest()


def create_password_reset_token(
    user_id: int,
    email: str,
    hashed_password: str,
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "email": email.strip().lower(),
        "pwd": _password_fingerprint(hashed_password),
        "iat": now,
        "exp": now
        + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
        ),
        "type": "password_reset",
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_password_reset_token(
    token: str,
) -> dict | None:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        if payload.get("type") != "password_reset":
            return None

        if not payload.get("sub"):
            return None

        if not payload.get("email"):
            return None

        if not payload.get("pwd"):
            return None

        return payload

    except JWTError:
        return None


def password_reset_token_matches_hash(
    token_fingerprint: str,
    hashed_password: str,
) -> bool:
    expected = _password_fingerprint(hashed_password)

    return hmac.compare_digest(
        token_fingerprint,
        expected,
    )
