from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from ..constants import (
    LAN_BOOTSTRAP_MATERIAL,
    LAN_PASSWORD_INCORRECT,
    LAN_PASSWORD_RESPONSE,
    LAN_PASSWORD_SUCCESS,
    SECURITY_AES_CBC,
    SECURITY_AES_ECB,
    SECURITY_PLAINTEXT,
)
from ..crypto.aes import (
    decrypt_cbc,
    decrypt_ecb,
)
from ..crypto.curve25519 import Curve25519Session
from ..packet import CommonPacket


@dataclass(frozen=True)
class LanPasswordResult:
    request_id: int
    method_id: int
    result_code: int

    sid: int
    perm: int
    origin: int

    camera_public_key: bytes
    shared_secret: bytes

    raw_json: dict[str, Any]


def decrypt_lan_password_payload(
    packet: CommonPacket,
) -> bytes:
    if packet.security_mode == SECURITY_PLAINTEXT:
        return packet.payload.rstrip(b"\x00")

    key = LAN_BOOTSTRAP_MATERIAL[:16]
    iv = LAN_BOOTSTRAP_MATERIAL[16:32]

    if packet.security_mode == SECURITY_AES_ECB:
        return decrypt_ecb(
            packet.payload,
            key,
        ).rstrip(b"\x00")

    if packet.security_mode == SECURITY_AES_CBC:
        return decrypt_cbc(
            packet.payload,
            key,
            iv,
        ).rstrip(b"\x00")

    raise ValueError(
        "Unsupported LAN-password response security mode: "
        f"{packet.security_mode}"
    )


def _require_integer(
    source: dict[str, Any],
    name: str,
) -> int:
    value = source.get(name)

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"Expected integer field {name!r}."
        )

    return value


def parse_lan_password_response(
    *,
    packet: CommonPacket,
    expected_request_id: int,
    curve_session: Curve25519Session,
) -> LanPasswordResult:
    plaintext = decrypt_lan_password_payload(packet)

    try:
        text = plaintext.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "LAN-password response is not valid UTF-8."
        ) from error

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"LAN-password response is invalid JSON: {error}"
        ) from error

    if not isinstance(document, dict):
        raise ValueError(
            "LAN-password response root must be an object."
        )

    response_id = _require_integer(
        document,
        "id",
    )

    channel = _require_integer(
        document,
        "chn",
    )

    method_id = _require_integer(
        document,
        "method_id",
    )

    if response_id != expected_request_id:
        raise ValueError(
            "LAN-password response ID does not match the request: "
            f"{response_id} != {expected_request_id}"
        )

    if channel not in (0, 1):
        raise ValueError(
            f"Unexpected LAN-password response channel: {channel}"
        )

    if method_id != LAN_PASSWORD_RESPONSE:
        raise ValueError(
            "Unexpected LAN-password response method: "
            f"{method_id} / 0x{method_id:x}"
        )

    result_object = document.get("result")

    if not isinstance(result_object, dict):
        raise ValueError(
            "LAN-password response does not contain a result object."
        )

    result_code = _require_integer(
        result_object,
        "code",
    )

    if result_code == LAN_PASSWORD_INCORRECT:
        raise PermissionError(
            "Camera rejected the LAN password."
        )

    if result_code != LAN_PASSWORD_SUCCESS:
        raise ValueError(
            "Camera returned LAN-password result code "
            f"{result_code}."
        )

    data = document.get("data")

    if not isinstance(data, dict):
        raise ValueError(
            "LAN-password response does not contain data."
        )

    verify = data.get("verify")

    if not isinstance(verify, dict):
        raise ValueError(
            "LAN-password response does not contain data.verify."
        )

    dk = verify.get("dK")
    ds = verify.get("dS")

    if not isinstance(dk, str):
        raise ValueError(
            "LAN-password response dK is missing."
        )

    if not isinstance(ds, str):
        raise ValueError(
            "LAN-password response dS is missing."
        )

    try:
        camera_public_key = base64.b64decode(
            dk,
            validate=True,
        )
    except ValueError as error:
        raise ValueError(
            "LAN-password response dK is invalid Base64."
        ) from error

    if len(camera_public_key) != 32:
        raise ValueError(
            "Decoded camera public key must be 32 bytes; "
            f"received {len(camera_public_key)}."
        )

    expected_ds = base64.b64encode(
        hashlib.sha256(camera_public_key).digest()
    ).decode("ascii")

    if ds != expected_ds:
        raise ValueError(
            "Camera public-key signature dS did not match."
        )

    shared_secret = curve_session.create_shared_secret(
        camera_public_key
    )

    sid = _require_integer(
        verify,
        "sid",
    )

    perm_value = verify.get("perm", 0)
    origin_value = verify.get("origin", 0)

    perm = (
        perm_value
        if isinstance(perm_value, int)
        and not isinstance(perm_value, bool)
        else 0
    )

    origin = (
        origin_value
        if isinstance(origin_value, int)
        and not isinstance(origin_value, bool)
        else 0
    )

    return LanPasswordResult(
        request_id=response_id,
        method_id=method_id,
        result_code=result_code,
        sid=sid,
        perm=perm,
        origin=origin,
        camera_public_key=camera_public_key,
        shared_secret=shared_secret,
        raw_json=document,
    )