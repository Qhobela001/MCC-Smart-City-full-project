from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping
from typing import Any


DEVICE_LIST_SIGNING_SECRET = "hsshop2016"


def create_unix_timestamp() -> int:
    return int(time.time())


def normalize_signing_value(
    value: Any,
) -> str:
    """
    Convert Python values to the string representation expected
    by the Java request-signing code.
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def build_device_list_signing_text(
    *,
    access_token: str,
    from_app: int,
    get_sub_server: int,
    language: str,
    registration_id: str,
    timestamp: int,
    device_type: str,
    version: int,
    secret: str = DEVICE_LIST_SIGNING_SECRET,
) -> str:
    """
    Build the exact ordered string used by the recovered
    updateUserDeviceList() implementation.

    Field order:

        accesstoken
        from_app
        get_sub_server
        language
        registrationid
        timestamp
        type
        ver
        secret
    """

    if not access_token:
        raise ValueError(
            "Access token cannot be empty."
        )

    if not secret:
        raise ValueError(
            "Signing secret cannot be empty."
        )

    parts = (
        f"accesstoken={access_token}",
        f"from_app={from_app}",
        f"get_sub_server={get_sub_server}",
        f"language={language}",
        f"registrationid={registration_id}",
        f"timestamp={timestamp}",
        f"type={device_type}",
        f"ver={version}",
    )

    return "&".join(parts) + secret


def calculate_md5_hex(
    value: str,
) -> str:
    return hashlib.md5(
        value.encode("utf-8")
    ).hexdigest()


def calculate_device_list_signature(
    *,
    access_token: str,
    from_app: int,
    get_sub_server: int,
    language: str,
    registration_id: str,
    timestamp: int,
    device_type: str = "all",
    version: int = 1008,
    secret: str = DEVICE_LIST_SIGNING_SECRET,
) -> str:
    signing_text = build_device_list_signing_text(
        access_token=access_token,
        from_app=from_app,
        get_sub_server=get_sub_server,
        language=language,
        registration_id=registration_id,
        timestamp=timestamp,
        device_type=device_type,
        version=version,
        secret=secret,
    )

    return calculate_md5_hex(signing_text)


def calculate_sorted_signature(
    values: Mapping[str, Any],
    *,
    secret: str,
) -> str:
    """
    Generic helper for later cloud endpoints.

    Do not use this for /device/list unless evidence shows that
    the application switched from its recovered fixed field order.
    """

    if not secret:
        raise ValueError(
            "Signing secret cannot be empty."
        )

    pairs = [
        (
            str(name),
            normalize_signing_value(value),
        )
        for name, value in values.items()
        if name != "sign"
    ]

    pairs.sort(
        key=lambda item: item[0]
    )

    signing_text = "&".join(
        f"{name}={value}"
        for name, value in pairs
    )

    return calculate_md5_hex(
        signing_text + secret
    )