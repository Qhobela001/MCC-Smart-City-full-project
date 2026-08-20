from __future__ import annotations

import struct
from dataclasses import dataclass

from .constants import (
    COMMON_HEADER_SIZE,
    MAX_PAYLOAD_SIZE,
)


_COMMON_HEADER = struct.Struct("<IBBBBII")


@dataclass(frozen=True)
class CommonPacket:
    command: int
    version: int
    security_mode: int
    field_6: int
    field_7: int
    reserved: int
    payload: bytes

    @property
    def payload_size(self) -> int:
        return len(self.payload)


def build_common_packet(
    payload: bytes,
    *,
    command: int,
    version: int = 1,
    security_mode: int = 0,
    field_6: int = 0,
    field_7: int = 0,
    reserved: int = 0,
) -> bytes:
    if not isinstance(payload, bytes):
        raise TypeError("payload must be bytes")

    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(
            f"Payload is too large: {len(payload)} bytes."
        )

    for name, value in (
        ("version", version),
        ("security_mode", security_mode),
        ("field_6", field_6),
        ("field_7", field_7),
    ):
        if not 0 <= value <= 0xFF:
            raise ValueError(f"{name} must fit in one byte")

    header = _COMMON_HEADER.pack(
        command,
        version,
        security_mode,
        field_6,
        field_7,
        reserved,
        len(payload),
    )

    if len(header) != COMMON_HEADER_SIZE:
        raise AssertionError("Common header is not 16 bytes.")

    return header + payload


def parse_common_header(header: bytes) -> CommonPacket:
    if len(header) != COMMON_HEADER_SIZE:
        raise ValueError(
            f"Expected {COMMON_HEADER_SIZE} header bytes, "
            f"received {len(header)}."
        )

    (
        command,
        version,
        security_mode,
        field_6,
        field_7,
        reserved,
        payload_size,
    ) = _COMMON_HEADER.unpack(header)

    if payload_size > MAX_PAYLOAD_SIZE:
        raise ValueError(
            f"Camera announced an unreasonable payload size: "
            f"{payload_size} bytes."
        )

    # The payload is attached later by receive_common_packet().
    return CommonPacket(
        command=command,
        version=version,
        security_mode=security_mode,
        field_6=field_6,
        field_7=field_7,
        reserved=reserved,
        payload=b"",
    )


def unpack_common_header(
    header: bytes,
) -> tuple[CommonPacket, int]:
    packet = parse_common_header(header)

    payload_size = struct.unpack_from("<I", header, 12)[0]

    return packet, payload_size