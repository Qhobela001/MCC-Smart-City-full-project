from __future__ import annotations

import secrets
import string
import struct
from dataclasses import dataclass
from datetime import datetime

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

from ..constants import (
    LOGIN_PACKET_SIZE,
    LOGIN_REQUEST,
    LOGIN_RESPONSE,
    LOGIN_SUCCESS_CODE,
)
from ..socket_client import CameraSocket


FIXED_LOGIN_KEY = b"macrovideo+*#!^@"


@dataclass(frozen=True)
class LoginSession:
    command: int
    result_code: int
    result_value: int
    version: int
    handle: int
    session_token: int
    device_type: int
    camera_type: int
    lan_flag: int
    domain: str
    lan_address: str
    channel_count: int
    capabilities: bytes
    raw_response: bytes

    @property
    def authenticated(self) -> bool:
        return (
            self.command == LOGIN_RESPONSE
            and self.result_code == LOGIN_SUCCESS_CODE
            and self.result_value == 0
        )


def _aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    if len(key) not in (16, 24, 32):
        raise ValueError(
            f"Invalid AES key length: {len(key)} bytes."
        )

    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(
        pad(data, AES.block_size)
    )


def _make_random_key(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def _copy_fixed(
    packet: bytearray,
    *,
    offset: int,
    field_size: int,
    value: bytes,
) -> None:
    if len(value) > field_size:
        raise ValueError(
            f"Value at offset {offset} is {len(value)} bytes; "
            f"maximum is {field_size}."
        )

    packet[offset : offset + len(value)] = value


def _encrypt_password(
    password: str,
    random_key: str,
) -> bytes:
    first_stage = _aes_ecb_encrypt(
        password.encode("utf-8"),
        FIXED_LOGIN_KEY,
    )

    return _aes_ecb_encrypt(
        first_stage,
        random_key.encode("ascii"),
    )


def build_login_packet(
    *,
    device_id: int,
    username: str,
    password: str,
) -> tuple[bytes, str]:
    packet = bytearray(LOGIN_PACKET_SIZE)
    random_key = _make_random_key()

    struct.pack_into(
        "<I",
        packet,
        0,
        LOGIN_REQUEST,
    )

    struct.pack_into(
        "<I",
        packet,
        4,
        120,
    )

    packet[8] = 31

    struct.pack_into(
        "<I",
        packet,
        9,
        10,
    )

    struct.pack_into(
        "<I",
        packet,
        13,
        device_id,
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    ).encode("ascii")

    encrypted_password = _encrypt_password(
        password,
        random_key,
    )

    _copy_fixed(
        packet,
        offset=17,
        field_size=32,
        value=timestamp,
    )

    _copy_fixed(
        packet,
        offset=49,
        field_size=32,
        value=username.encode("utf-8"),
    )

    _copy_fixed(
        packet,
        offset=81,
        field_size=16,
        value=random_key.encode("ascii"),
    )

    _copy_fixed(
        packet,
        offset=97,
        field_size=32,
        value=encrypted_password,
    )

    return bytes(packet), random_key


def _decode_null_terminated(data: bytes) -> str:
    return data.split(
        b"\x00",
        1,
    )[0].decode(
        "ascii",
        errors="replace",
    ).strip()


def parse_login_response(
    response: bytes,
) -> LoginSession:
    if len(response) != LOGIN_PACKET_SIZE:
        raise ValueError(
            f"Expected {LOGIN_PACKET_SIZE} login-response bytes, "
            f"received {len(response)}."
        )

    return LoginSession(
        command=struct.unpack_from(
            "<I",
            response,
            0,
        )[0],
        result_code=struct.unpack_from(
            "<I",
            response,
            4,
        )[0],
        result_value=struct.unpack_from(
            "<i",
            response,
            8,
        )[0],
        version=response[12],
        handle=struct.unpack_from(
            "<I",
            response,
            13,
        )[0],
        session_token=struct.unpack_from(
            "<I",
            response,
            17,
        )[0],
        device_type=response[21],
        camera_type=response[22],
        lan_flag=response[25],
        domain=_decode_null_terminated(
            response[26:58]
        ),
        lan_address=_decode_null_terminated(
            response[62:94]
        ),
        channel_count=response[98],
        capabilities=response[106:138],
        raw_response=response,
    )


def login(
    camera: CameraSocket,
    *,
    device_id: int,
    username: str,
    password: str,
) -> LoginSession:
    packet, random_key = build_login_packet(
        device_id=device_id,
        username=username,
        password=password,
    )

    print(f"Generated login random key: {random_key}")
    print(f"Sending login packet: {len(packet)} bytes")

    camera.send_all(packet)

    response = camera.receive_exact(
        LOGIN_PACKET_SIZE
    )

    session = parse_login_response(response)

    if not session.authenticated:
        raise PermissionError(
            "Camera authentication failed: "
            f"command={session.command}, "
            f"result_code={session.result_code}, "
            f"result_value={session.result_value}"
        )

    return session