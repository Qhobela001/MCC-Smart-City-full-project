from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any

from .client import V380CloudClient
from .password_crypto import encrypt_login_password_hex


ACCOUNT_LOGIN_PATH = "user/login"
ACCOUNT_LOGIN_SIGNING_SECRET = "hsshop2016"
DEFAULT_PHONE_TOKEN = "100"


@dataclass(frozen=True)
class AccountLoginRequest:
    username: str
    encrypted_password: str
    phone_token: str
    timestamp: int
    signature: str
    document: dict[str, Any]


@dataclass(frozen=True)
class AccountLoginResult:
    result: int
    error_code: int
    access_token: str
    user_id: int
    username: str
    raw_document: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        return (
            self.result == 0
            and bool(self.access_token)
        )


def create_account_login_signature(
    *,
    username: str,
    encrypted_password: str,
    phone_token: str,
    timestamp: int,
    secret: str = ACCOUNT_LOGIN_SIGNING_SECRET,
) -> str:
    """
    Reproduce the recovered Java signing text:

        password=<encrypted_password>
        &phonetoken=<phone_token>
        &timestamp=<timestamp>
        &username=<username>
        hsshop2016

    There is intentionally no ampersand before the final secret.
    """

    if not username:
        raise ValueError(
            "V380 account username cannot be empty."
        )

    if not encrypted_password:
        raise ValueError(
            "Encrypted account password cannot be empty."
        )

    if not phone_token:
        raise ValueError(
            "Phone token cannot be empty."
        )

    if timestamp <= 0:
        raise ValueError(
            "Login timestamp must be positive."
        )

    if not secret:
        raise ValueError(
            "Login signing secret cannot be empty."
        )

    signing_text = (
        f"password={encrypted_password}"
        f"&phonetoken={phone_token}"
        f"&timestamp={timestamp}"
        f"&username={username}"
        f"{secret}"
    )

    return hashlib.md5(
        signing_text.encode("utf-8")
    ).hexdigest()


def build_account_login_request(
    *,
    username: str,
    password: str,
    phone_token: str = DEFAULT_PHONE_TOKEN,
    timestamp: int | None = None,
) -> AccountLoginRequest:
    if not username:
        raise ValueError(
            "V380 account username cannot be empty."
        )

    if not password:
        raise ValueError(
            "V380 account password cannot be empty."
        )

    resolved_timestamp = (
        int(time.time())
        if timestamp is None
        else timestamp
    )

    encrypted_password = (
        encrypt_login_password_hex(
            password
        )
    )

    signature = create_account_login_signature(
        username=username,
        encrypted_password=encrypted_password,
        phone_token=phone_token,
        timestamp=resolved_timestamp,
    )

    document: dict[str, Any] = {
        "username": username,
        "password": encrypted_password,
        "phonetoken": phone_token,
        "sign": signature,
        "timestamp": resolved_timestamp,
    }

    return AccountLoginRequest(
        username=username,
        encrypted_password=encrypted_password,
        phone_token=phone_token,
        timestamp=resolved_timestamp,
        signature=signature,
        document=document,
    )


def login_account(
    client: V380CloudClient,
    *,
    username: str,
    password: str,
    phone_token: str = DEFAULT_PHONE_TOKEN,
    timestamp: int | None = None,
) -> AccountLoginResult:
    request = build_account_login_request(
        username=username,
        password=password,
        phone_token=phone_token,
        timestamp=timestamp,
    )

    response_document = client.post_json(
        ACCOUNT_LOGIN_PATH,
        request.document,
    )

    return parse_account_login_response(
        response_document,
        fallback_username=username,
    )


def parse_account_login_response(
    document: dict[str, Any],
    *,
    fallback_username: str = "",
) -> AccountLoginResult:
    result = _read_first_integer(
        document,
        (
            "result",
            "code",
        ),
        default=-1,
    )

    error_code = _read_first_integer(
        document,
        (
            "error_code",
            "errorCode",
        ),
        default=0,
    )

    data = document.get("data")

    if not isinstance(data, dict):
        data = {}

    access_token = _read_first_string_from_documents(
        (document, data),
        (
            "access_token",
            "accesstoken",
            "accessToken",
            "token",
        ),
        default="",
    )

    user_id = _read_first_integer_from_documents(
        (document, data),
        (
            "userid",
            "user_id",
            "uid",
            "id",
        ),
        default=0,
    )

    username = _read_first_string_from_documents(
        (document, data),
        (
            "username",
            "account",
            "user_name",
        ),
        default=fallback_username,
    )

    return AccountLoginResult(
        result=result,
        error_code=error_code,
        access_token=access_token,
        user_id=user_id,
        username=username,
        raw_document=document,
    )


def _read_first_integer(
    document: dict[str, Any],
    names: tuple[str, ...],
    *,
    default: int,
) -> int:
    for name in names:
        if name not in document:
            continue

        value = document[name]

        if isinstance(value, bool):
            continue

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            if value.is_integer():
                return int(value)

        if isinstance(value, str):
            try:
                return int(value.strip())
            except ValueError:
                continue

    return default


def _read_first_integer_from_documents(
    documents: tuple[dict[str, Any], ...],
    names: tuple[str, ...],
    *,
    default: int,
) -> int:
    for document in documents:
        value = _read_first_integer(
            document,
            names,
            default=default,
        )

        if value != default:
            return value

    return default


def _read_first_string_from_documents(
    documents: tuple[dict[str, Any], ...],
    names: tuple[str, ...],
    *,
    default: str,
) -> str:
    for document in documents:
        for name in names:
            value = document.get(name)

            if isinstance(value, str):
                cleaned = value.strip()

                if cleaned:
                    return cleaned

            elif value is not None:
                return str(value)

    return default