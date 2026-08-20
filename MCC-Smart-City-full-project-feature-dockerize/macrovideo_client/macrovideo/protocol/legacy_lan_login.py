from __future__ import annotations

import secrets
import socket
import string
import struct
from dataclasses import dataclass
from datetime import datetime
from typing import Final

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


LOGIN_PACKET_SIZE: Final[int] = 256

# LoginHelper static values recovered from the Android SDK.
LOGIN_REQUEST_COMMAND: Final[int] = 1167
LOGIN_RESPONSE_COMMAND: Final[int] = 1168
PHONE_TYPE: Final[int] = 120
LOGIN_PROTOCOL_VERSION: Final[int] = 31
ACCOUNT_ID: Final[int] = 10
PASSWORD_STAGE_ONE_KEY: Final[bytes] = b"macrovideo+*#!^@"

# Request offsets from LoginHelper.m21515b().
OFFSET_COMMAND: Final[int] = 0
OFFSET_PHONE_TYPE: Final[int] = 4
OFFSET_VERSION: Final[int] = 8
OFFSET_ACCOUNT_ID: Final[int] = 9
OFFSET_DEVICE_ID: Final[int] = 13
OFFSET_DATETIME: Final[int] = 17
OFFSET_USERNAME: Final[int] = 49
OFFSET_RANDOM_KEY: Final[int] = 81
OFFSET_PASSWORD: Final[int] = 97

DATETIME_FIELD_SIZE: Final[int] = 32
USERNAME_FIELD_SIZE: Final[int] = 32
RANDOM_KEY_SIZE: Final[int] = 16
PASSWORD_FIELD_SIZE: Final[int] = 64


@dataclass(frozen=True)
class LegacyLanLoginRequest:
    device_id: int
    username: str
    timestamp_text: str
    random_key: str
    encrypted_password: bytes
    packet: bytes


@dataclass(frozen=True)
class LegacyLanLoginResponse:
    raw_packet: bytes
    command: int
    login_result: int
    result_value: int
    protocol_version: int
    handle: int
    token_session: int
    device_type: int
    camera_type: int
    channel_count: int
    succeeded: bool
    normalized_error: int


@dataclass(frozen=True)
class LegacyLanLoginExchange:
    host: str
    port: int
    request: LegacyLanLoginRequest
    response: LegacyLanLoginResponse


def build_legacy_lan_login_request(
        *,
        device_id: int,
        username: str,
        password: str,
        timestamp_text: str | None = None,
        random_key: str | None = None,
) -> LegacyLanLoginRequest:
    """
    Reproduce LoginHelper.m21515b() / LoginFromServerEX.

    Layout:
        0x00 int32  command=1167
        0x04 int32  phone type=120
        0x08 uint8  protocol version=31
        0x09 int32  account id=10
        0x0d int32  device id
        0x11 bytes  local datetime text
        0x31 bytes  camera username
        0x51 bytes  random 16-byte ASCII key
        0x61 bytes  AES(AES(password, fixed_key), random_key)
    """

    if device_id <= 0:
        raise ValueError("Device ID must be positive.")

    resolved_username = username.strip()
    if not resolved_username:
        raise ValueError("Camera username cannot be empty.")

    # Blank camera LAN passwords are valid on some V380 devices.
    # Keep the empty string and let the existing AES/PKCS7 routine
    # generate the protocol-correct encrypted password field.

    resolved_timestamp = (
        timestamp_text
        if timestamp_text is not None
        else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    resolved_random_key = (
        random_key
        if random_key is not None
        else _random_ascii(RANDOM_KEY_SIZE)
    )

    _validate_ascii_field(
        "timestamp",
        resolved_timestamp,
        DATETIME_FIELD_SIZE,
    )
    _validate_ascii_field(
        "username",
        resolved_username,
        USERNAME_FIELD_SIZE,
    )
    _validate_ascii_field(
        "random key",
        resolved_random_key,
        RANDOM_KEY_SIZE,
        exact=True,
    )

    stage_one = _aes_ecb_pkcs7_encrypt(
        password.encode("utf-8"),
        PASSWORD_STAGE_ONE_KEY,
    )
    encrypted_password = _aes_ecb_pkcs7_encrypt(
        stage_one,
        resolved_random_key.encode("ascii"),
    )

    if len(encrypted_password) > PASSWORD_FIELD_SIZE:
        raise ValueError(
            "Encrypted camera password exceeds the "
            f"{PASSWORD_FIELD_SIZE}-byte packet field."
        )

    packet = bytearray(LOGIN_PACKET_SIZE)

    _put_i32_le(packet, OFFSET_COMMAND, LOGIN_REQUEST_COMMAND)
    _put_i32_le(packet, OFFSET_PHONE_TYPE, PHONE_TYPE)
    packet[OFFSET_VERSION] = LOGIN_PROTOCOL_VERSION
    _put_i32_le(packet, OFFSET_ACCOUNT_ID, ACCOUNT_ID)
    _put_i32_le(packet, OFFSET_DEVICE_ID, device_id)

    _put_ascii(
        packet,
        OFFSET_DATETIME,
        DATETIME_FIELD_SIZE,
        resolved_timestamp,
    )
    _put_ascii(
        packet,
        OFFSET_USERNAME,
        USERNAME_FIELD_SIZE,
        resolved_username,
    )
    _put_ascii(
        packet,
        OFFSET_RANDOM_KEY,
        RANDOM_KEY_SIZE,
        resolved_random_key,
    )

    packet[
        OFFSET_PASSWORD:
        OFFSET_PASSWORD + len(encrypted_password)
    ] = encrypted_password

    return LegacyLanLoginRequest(
        device_id=device_id,
        username=resolved_username,
        timestamp_text=resolved_timestamp,
        random_key=resolved_random_key,
        encrypted_password=encrypted_password,
        packet=bytes(packet),
    )


def parse_legacy_lan_login_response(
        packet: bytes,
) -> LegacyLanLoginResponse:
    if len(packet) != LOGIN_PACKET_SIZE:
        raise ValueError(
            "Legacy LAN login response must be exactly "
            f"{LOGIN_PACKET_SIZE} bytes; received {len(packet)}."
        )

    command = _get_i32_le(packet, 0)
    login_result = _get_i32_le(packet, 4)
    result_value = _get_i32_le(packet, 8)

    protocol_version = packet[12]
    handle = _get_u32_le(packet, 13)
    token_session = _get_u32_le(packet, 17)
    device_type = packet[21]
    camera_type = packet[22]
    channel_count = packet[63]

    # Android normalizes result_value by removing its hundreds.
    normalized_error = result_value - int(result_value / 100) * 100

    succeeded = (
            command == LOGIN_RESPONSE_COMMAND
            and login_result == 1001
            and normalized_error == 0
    )

    return LegacyLanLoginResponse(
        raw_packet=packet,
        command=command,
        login_result=login_result,
        result_value=result_value,
        protocol_version=protocol_version,
        handle=handle,
        token_session=token_session,
        device_type=device_type,
        camera_type=camera_type,
        channel_count=channel_count,
        succeeded=succeeded,
        normalized_error=normalized_error,
    )


def perform_legacy_lan_login(
        *,
        host: str,
        port: int,
        device_id: int,
        username: str,
        password: str,
        connect_timeout: float = 8.0,
        read_timeout: float = 8.0,
) -> LegacyLanLoginExchange:
    resolved_host = host.strip()

    if not resolved_host:
        raise ValueError("Camera host cannot be empty.")

    if not 1 <= port <= 65535:
        raise ValueError("Camera port must be between 1 and 65535.")

    request = build_legacy_lan_login_request(
        device_id=device_id,
        username=username,
        password=password,
    )

    print(f"[LAN] Connecting to {resolved_host}:{port}")
    print(f"[LAN] Timestamp: {request.timestamp_text}")
    print(f"[LAN] Username: {request.username}")
    print(f"[LAN] Random key: {request.random_key}")
    print(
        "[LAN] Encrypted password length: "
        f"{len(request.encrypted_password)} bytes"
    )
    print(
        "[LAN] Request first 32 bytes: "
        f"{request.packet[:32].hex()}"
    )
    print(
        "[LAN] Complete request size: "
        f"{len(request.packet)} bytes"
    )

    try:
        with socket.create_connection(
                (resolved_host, port),
                timeout=connect_timeout,
        ) as sock:
            sock.settimeout(read_timeout)

            print("[LAN] TCP connection established.")
            sock.sendall(request.packet)
            print("[LAN] 256-byte login packet sent.")

            response_packet = _recv_exact(
                sock,
                LOGIN_PACKET_SIZE,
            )

    except socket.timeout as error:
        raise TimeoutError(
            "Timed out waiting for the camera's "
            "256-byte login response."
        ) from error
    except OSError as error:
        raise ConnectionError(
            "Legacy LAN login network failure for "
            f"{resolved_host}:{port}: {error}"
        ) from error

    response = parse_legacy_lan_login_response(
        response_packet
    )

    return LegacyLanLoginExchange(
        host=resolved_host,
        port=port,
        request=request,
        response=response,
    )


def _aes_ecb_pkcs7_encrypt(
        plaintext: bytes,
        key: bytes,
) -> bytes:
    if len(key) not in {16, 24, 32}:
        raise ValueError(
            "AES key must contain 16, 24, or 32 bytes."
        )

    padder = padding.PKCS7(
        algorithms.AES.block_size
    ).padder()

    padded = (
            padder.update(plaintext)
            + padder.finalize()
    )

    encryptor = Cipher(
        algorithms.AES(key),
        modes.ECB(),
    ).encryptor()

    return (
            encryptor.update(padded)
            + encryptor.finalize()
    )


def _random_ascii(length: int) -> str:
    alphabet = (
            string.ascii_letters
            + string.digits
    )
    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )


def _validate_ascii_field(
        name: str,
        value: str,
        size: int,
        *,
        exact: bool = False,
) -> None:
    try:
        encoded = value.encode("ascii")
    except UnicodeEncodeError as error:
        raise ValueError(
            f"{name.capitalize()} must contain ASCII characters only."
        ) from error

    if exact and len(encoded) != size:
        raise ValueError(
            f"{name.capitalize()} must be exactly {size} bytes."
        )

    if not exact and len(encoded) > size:
        raise ValueError(
            f"{name.capitalize()} exceeds its {size}-byte field."
        )


def _put_ascii(
        packet: bytearray,
        offset: int,
        size: int,
        value: str,
) -> None:
    encoded = value.encode("ascii")

    if len(encoded) > size:
        raise ValueError(
            f"Value at offset {offset} exceeds {size} bytes."
        )

    packet[offset:offset + len(encoded)] = encoded


def _put_i32_le(
        packet: bytearray,
        offset: int,
        value: int,
) -> None:
    struct.pack_into("<i", packet, offset, value)


def _get_i32_le(
        packet: bytes,
        offset: int,
) -> int:
    return struct.unpack_from("<i", packet, offset)[0]


def _get_u32_le(
        packet: bytes,
        offset: int,
) -> int:
    return struct.unpack_from("<I", packet, offset)[0]


def _recv_exact(
        sock: socket.socket,
        size: int,
) -> bytes:
    buffer = bytearray()

    while len(buffer) < size:
        chunk = sock.recv(size - len(buffer))

        if not chunk:
            raise ConnectionError(
                "Camera closed the connection after "
                f"{len(buffer)} of {size} expected bytes."
            )

        buffer.extend(chunk)

    return bytes(buffer)