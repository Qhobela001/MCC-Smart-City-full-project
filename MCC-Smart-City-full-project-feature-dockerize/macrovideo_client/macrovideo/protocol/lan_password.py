from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..constants import (
    COMMON_JSON_COMMAND,
    LAN_BOOTSTRAP_MATERIAL,
    LAN_PASSWORD_REQUEST,
    SECURITY_AES_CBC,
)
from ..crypto.aes import encrypt_cbc
from ..crypto.curve25519 import Curve25519Session
from ..packet import build_common_packet


@dataclass(frozen=True)
class LanPasswordRequest:
    request_id: int
    magic: int
    timestamp: int
    timezone: str

    client_seed: bytes
    client_public_key: bytes
    masked_public_key: bytes

    ckm: str
    cs: str

    params: dict[str, Any]
    raw_json: bytes
    encrypted_payload: bytes
    packet: bytes


def create_magic_number() -> int:
    """
    Equivalent to:

        new Random().nextInt(127) + 1

    Valid range: 1 through 127.
    """

    return secrets.randbelow(127) + 1


def create_request_id() -> int:
    """
    Produce a positive request ID.

    The Android implementation adds 10 to a bounded random integer.
    """

    return secrets.randbelow(0x7FFFFFFF - 10) + 10


def get_local_timezone_string() -> str:
    """
    Produce a timezone offset such as:

        +02:00
        -05:30
    """

    offset = datetime.now().astimezone().utcoffset()

    if offset is None:
        return "+00:00"

    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"

    absolute_seconds = abs(total_seconds)
    hours, remainder = divmod(absolute_seconds, 3600)
    minutes = remainder // 60

    return f"{sign}{hours:02d}:{minutes:02d}"


def xor_with_single_byte(
    data: bytes,
    value: int,
) -> bytes:
    if not 0 <= value <= 0xFF:
        raise ValueError(
            "XOR value must fit in one byte."
        )

    return bytes(
        byte ^ value
        for byte in data
    )


def _base64_no_wrap(data: bytes) -> str:
    return base64.b64encode(
        data
    ).decode("ascii")


def build_lan_password_request(
    *,
    password: str,
    curve_session: Curve25519Session | None = None,
    request_id: int | None = None,
    magic: int | None = None,
    timezone: str | None = None,
    timestamp: int | None = None,
) -> tuple[LanPasswordRequest, Curve25519Session]:
    if not password:
        raise ValueError(
            "Camera LAN password cannot be empty."
        )

    session = (
        curve_session
        if curve_session is not None
        else Curve25519Session()
    )

    key_pair = session.generate()

    resolved_magic = (
        create_magic_number()
        if magic is None
        else magic
    )

    if not 1 <= resolved_magic <= 127:
        raise ValueError(
            "LAN-password magic number must be "
            "from 1 through 127."
        )

    resolved_request_id = (
        create_request_id()
        if request_id is None
        else request_id
    )

    resolved_timestamp = (
        int(time.time())
        if timestamp is None
        else timestamp
    )

    resolved_timezone = (
        get_local_timezone_string()
        if timezone is None
        else timezone
    )

    masked_public_key = xor_with_single_byte(
        key_pair.public_key,
        resolved_magic,
    )

    ckm = _base64_no_wrap(
        masked_public_key
    )

    signature_input = (
        masked_public_key
        + password.encode("utf-8")
    )

    cs = _base64_no_wrap(
        hashlib.sha256(
            signature_input
        ).digest()
    )

    params: dict[str, Any] = {
        "act": 1,
        "verify": {
            "cKM": ckm,
            "cS": cs,
            "tz": resolved_timezone,
            "ts": resolved_timestamp,
        },
    }

    body = {
        "id": resolved_request_id,
        "method_id": LAN_PASSWORD_REQUEST,
        "chn": 1,
        "ts": resolved_timestamp,
        "params": params,
    }

    raw_json = json.dumps(
        body,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    if len(LAN_BOOTSTRAP_MATERIAL) != 32:
        raise AssertionError(
            "LAN bootstrap material must contain "
            "exactly 32 bytes."
        )

    aes_key = LAN_BOOTSTRAP_MATERIAL[:16]
    aes_iv = LAN_BOOTSTRAP_MATERIAL[16:32]

    print(
        "[debug] Bootstrap key:",
        aes_key.hex(),
    )
    print(
        "[debug] Bootstrap IV:",
        aes_iv.hex(),
    )
    print(
        "[debug] JSON bytes:",
        raw_json.hex(),
    )
    print(
        "[debug] JSON length:",
        len(raw_json),
    )

    encrypted_payload = encrypt_cbc(
        raw_json,
        aes_key,
        aes_iv,
    )

    packet = build_common_packet(
        encrypted_payload,
        command=COMMON_JSON_COMMAND,
        version=1,
        security_mode=SECURITY_AES_CBC,
        field_6=0,
        field_7=resolved_magic,
        reserved=0,
    )

    return (
        LanPasswordRequest(
            request_id=resolved_request_id,
            magic=resolved_magic,
            timestamp=resolved_timestamp,
            timezone=resolved_timezone,
            client_seed=key_pair.seed,
            client_public_key=key_pair.public_key,
            masked_public_key=masked_public_key,
            ckm=ckm,
            cs=cs,
            params=params,
            raw_json=raw_json,
            encrypted_payload=encrypted_payload,
            packet=packet,
        ),
        session,
    )