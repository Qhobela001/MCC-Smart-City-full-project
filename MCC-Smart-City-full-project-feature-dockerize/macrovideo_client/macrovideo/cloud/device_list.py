from __future__ import annotations

from typing import Any

from .client import V380CloudClient
from .models import (
    CloudDeviceInfo,
    DeviceListRequestOptions,
    DeviceListResult,
)
from .signing import (
    calculate_device_list_signature,
    create_unix_timestamp,
)


DEVICE_LIST_PATH = "device/list"


def build_device_list_request(
    options: DeviceListRequestOptions,
) -> dict[str, Any]:
    timestamp = (
        create_unix_timestamp()
        if options.timestamp is None
        else options.timestamp
    )

    signature = calculate_device_list_signature(
        access_token=options.access_token,
        from_app=options.from_app,
        get_sub_server=options.get_sub_server,
        language=options.language,
        registration_id=options.registration_id,
        timestamp=timestamp,
        device_type=options.device_type,
        version=options.version,
    )

    return {
        "accesstoken": options.access_token,
        "from_app": options.from_app,
        "get_sub_server": options.get_sub_server,
        "language": options.language,
        "registrationid": options.registration_id,
        "sign": signature,
        "timestamp": timestamp,
        "type": options.device_type,
        "ver": options.version,
    }


def fetch_device_list(
    client: V380CloudClient,
    options: DeviceListRequestOptions,
) -> DeviceListResult:
    request_document = build_device_list_request(
        options
    )

    response_document = client.post_json(
        DEVICE_LIST_PATH,
        request_document,
    )

    return parse_device_list_response(
        response_document
    )


def parse_device_list_response(
    document: dict[str, Any],
) -> DeviceListResult:
    result = _read_integer(
        document,
        "result",
        default=-1,
    )

    error_code = _read_integer(
        document,
        "error_code",
        default=0,
    )

    user_id = _read_integer(
        document,
        "user_id",
        default=0,
    )

    mqtt_enabled = _read_integer(
        document,
        "mqtt",
        default=0,
    )

    renew_token = _read_boolean(
        document,
        "renew_token",
        default=False,
    )

    set_username = _read_boolean(
        document,
        "set_username",
        default=False,
    )

    owned_documents = _read_list(
        document,
        "data",
    )

    shared_documents = _read_list(
        document,
        "data_share",
    )

    devices = tuple(
        _parse_device(
            item,
            default_from_user_id=user_id,
        )
        for item in owned_documents
        if isinstance(item, dict)
    )

    shared_devices = tuple(
        _parse_device(
            item,
            default_from_user_id=0,
        )
        for item in shared_documents
        if isinstance(item, dict)
    )

    return DeviceListResult(
        result=result,
        error_code=error_code,
        user_id=user_id,
        mqtt_enabled=mqtt_enabled,
        renew_token=renew_token,
        set_username=set_username,
        devices=devices,
        shared_devices=shared_devices,
        raw_document=document,
    )


def _parse_device(
    document: dict[str, Any],
    *,
    default_from_user_id: int,
) -> CloudDeviceInfo:
    device_id = _read_first_integer(
        document,
        (
            "device_id",
            "did",
        ),
        default=0,
    )

    if device_id <= 0:
        raise ValueError(
            "Device-list entry does not contain a valid "
            f"device ID: {document!r}"
        )

    mqsl = _read_first_string(
        document,
        (
            "mqsl",
        ),
        default="",
    )

    protocol_version = _read_first_integer(
        document,
        (
            "pver",
            "ver",
        ),
        default=0,
    )

    rand_key = _read_first_string(
        document,
        (
            "rk",
            "rand_key",
            "randKey",
        ),
        default="",
    )

    public_key = _read_first_string(
        document,
        (
            "public_key",
            "pKey",
            "pkey",
        ),
        default="",
    )

    from_user_id = _read_first_integer(
        document,
        (
            "from_user_id",
            "master_id",
        ),
        default=default_from_user_id,
    )



    account = _read_first_string(
        document,
        (
            "account",
            "username",
            "device_account",
        ),
        default="",
    )

    password = _read_first_string(
        document,
        (
            "pwd",
            "password",
            "device_password",
        ),
        default="",
    )

    nickname = _read_first_string(
        document,
        (
            "nickname",
            "name",
        ),
        default="",
    )

    model = _read_first_string(
        document,
        (
            "model",
            "device_model",
        ),
        default="",
    )

    return CloudDeviceInfo(
        device_id=device_id,
        mqsl=mqsl,
        protocol_version=protocol_version,
        rand_key=rand_key,
        public_key=public_key,
        from_user_id=from_user_id,
        account=account,
        password=password,
        nickname=nickname,
        model=model,
        raw_document=document,
    )


def _read_list(
    document: dict[str, Any],
    name: str,
) -> list[Any]:
    value = document.get(name)

    if isinstance(value, list):
        return value

    return []


def _read_integer(
    document: dict[str, Any],
    name: str,
    *,
    default: int,
) -> int:
    value = document.get(name)

    if isinstance(value, bool):
        return default

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        if value.is_integer():
            return int(value)

    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default

    return default


def _read_boolean(
    document: dict[str, Any],
    name: str,
    *,
    default: bool,
) -> bool:
    value = document.get(name)

    if isinstance(value, bool):
        return value

    if isinstance(value, int):
        return value != 0

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {
            "true",
            "1",
            "yes",
        }:
            return True

        if normalized in {
            "false",
            "0",
            "no",
        }:
            return False

    return default


def _read_first_integer(
    document: dict[str, Any],
    names: tuple[str, ...],
    *,
    default: int,
) -> int:
    for name in names:
        if name in document:
            return _read_integer(
                document,
                name,
                default=default,
            )

    return default


def _read_first_string(
    document: dict[str, Any],
    names: tuple[str, ...],
    *,
    default: str,
) -> str:
    for name in names:
        value = document.get(name)

        if isinstance(value, str):
            return value

        if value is not None:
            return str(value)

    return default