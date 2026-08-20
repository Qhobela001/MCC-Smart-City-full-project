from __future__ import annotations

import socket
import struct
from dataclasses import dataclass
from typing import Any, Final

from .legacy_config_parsers import (
    DecodedConfig,
    decode_config_payload,
    decoded_to_dict,
)


DEVICE_CONFIG_REQUEST_SIZE: Final[int] = 256
DEVICE_CONFIG_RESPONSE_HEADER_SIZE: Final[int] = 12
DEVICE_CONFIG_RECORD_HEADER_SIZE: Final[int] = 5
MAX_RECORD_PAYLOAD_SIZE: Final[int] = 512
CMD_GET_DEVICE_CONFIG_REQ: Final[int] = 365

CONFIG_TYPE_NAMES: Final[dict[int, str]] = {
    1: "INFO_NETWORK",
    2: "INFO_RECORD",
    3: "INFO_ALARM",
    4: "INFO_VERSION",
    5: "INFO_IP",
    6: "INFO_DATETIME",
    7: "INFO_MOTION_SENSITIVITY",
    8: "INFO_THERMAL",
    9: "INFO_PTZX_CRUISE",
    10: "INFO_WHITE_LIGHT",
    11: "INFO_PRIVATE_CONTROL",
    12: "INFO_TYPE_12_UNRESOLVED",
    13: "INFO_TYPE_13_UNRESOLVED",
    14: "INFO_AI_HUMAN_DETECT",
    15: "INFO_TIME_BACKTRACKING",
    16: "INFO_CPE",
    17: "INFO_CAR",
    18: "INFO_PET",
    19: "INFO_PIR_WAKEUP",
}


@dataclass(frozen=True)
class DeviceConfigRequest:
    device_id: int
    login_handle: int
    packet: bytes


@dataclass(frozen=True)
class DeviceConfigResponseHeader:
    command: int
    result: int
    version: int
    record_count: int
    raw: bytes


@dataclass(frozen=True)
class DeviceConfigRecord:
    prefix: int
    index: int
    config_type: int
    config_name: str
    payload_length: int
    payload: bytes
    raw_header: bytes
    decoded: DecodedConfig

    @property
    def decoded_document(self) -> dict[str, Any]:
        return decoded_to_dict(self.decoded)


@dataclass(frozen=True)
class DeviceConfigExchange:
    host: str
    port: int
    request: DeviceConfigRequest
    response_header: DeviceConfigResponseHeader
    records: tuple[DeviceConfigRecord, ...]

    @property
    def succeeded(self) -> bool:
        return (
            self.response_header.result == 1001
            and self.response_header.record_count > 0
            and len(self.records)
            == self.response_header.record_count
        )


def build_device_config_request(
    *,
    device_id: int,
    login_handle: int,
) -> DeviceConfigRequest:
    if device_id <= 0:
        raise ValueError("Device ID must be positive.")
    if login_handle <= 0:
        raise ValueError("Login handle must be positive.")

    packet = bytearray(DEVICE_CONFIG_REQUEST_SIZE)
    struct.pack_into("<i", packet, 0, CMD_GET_DEVICE_CONFIG_REQ)
    struct.pack_into("<i", packet, 4, device_id)
    packet[8] = 1
    struct.pack_into("<I", packet, 9, login_handle)

    return DeviceConfigRequest(
        device_id=device_id,
        login_handle=login_handle,
        packet=bytes(packet),
    )


def parse_device_config_response_header(
    raw: bytes,
) -> DeviceConfigResponseHeader:
    if len(raw) != DEVICE_CONFIG_RESPONSE_HEADER_SIZE:
        raise ValueError(
            "Device-config response header must be exactly "
            f"{DEVICE_CONFIG_RESPONSE_HEADER_SIZE} bytes; "
            f"received {len(raw)}."
        )

    command, result, version, record_count = struct.unpack(
        "<iihh",
        raw,
    )

    return DeviceConfigResponseHeader(
        command=command,
        result=result,
        version=version,
        record_count=record_count,
        raw=raw,
    )


def parse_device_config_record(
    *,
    raw_header: bytes,
    payload: bytes,
) -> DeviceConfigRecord:
    if len(raw_header) != DEVICE_CONFIG_RECORD_HEADER_SIZE:
        raise ValueError(
            "Configuration record header must be exactly "
            f"{DEVICE_CONFIG_RECORD_HEADER_SIZE} bytes."
        )

    prefix = raw_header[0]
    index = raw_header[1]
    config_type = raw_header[2]
    payload_length = struct.unpack_from(
        "<H",
        raw_header,
        3,
    )[0]

    if payload_length != len(payload):
        raise ValueError(
            "Configuration record payload length mismatch: "
            f"header={payload_length}, actual={len(payload)}."
        )

    try:
        decoded = decode_config_payload(
            config_type,
            payload,
        )
    except (IndexError, struct.error, ValueError):
        from .legacy_config_parsers import RawConfig

        decoded = RawConfig(
            config_type=config_type,
            payload_hex=payload.hex(),
        )

    return DeviceConfigRecord(
        prefix=prefix,
        index=index,
        config_type=config_type,
        config_name=CONFIG_TYPE_NAMES.get(
            config_type,
            f"UNKNOWN_TYPE_{config_type}",
        ),
        payload_length=payload_length,
        payload=payload,
        raw_header=raw_header,
        decoded=decoded,
    )


def perform_device_config_request(
    *,
    host: str,
    port: int,
    device_id: int,
    login_handle: int,
    connect_timeout: float = 5.0,
    read_timeout: float = 8.0,
) -> DeviceConfigExchange:
    resolved_host = host.strip()

    if not resolved_host:
        raise ValueError("Camera host cannot be empty.")
    if not 1 <= port <= 65535:
        raise ValueError("Camera port must be between 1 and 65535.")

    request = build_device_config_request(
        device_id=device_id,
        login_handle=login_handle,
    )

    print(f"[CONFIG] Connecting to {resolved_host}:{port}")
    print(f"[CONFIG] Request command: {CMD_GET_DEVICE_CONFIG_REQ}")
    print(f"[CONFIG] Device ID: {device_id}")
    print(f"[CONFIG] Login handle: {login_handle}")

    try:
        with socket.create_connection(
            (resolved_host, port),
            timeout=connect_timeout,
        ) as sock:
            sock.settimeout(read_timeout)
            sock.sendall(request.packet)

            raw_header = _recv_exact(
                sock,
                DEVICE_CONFIG_RESPONSE_HEADER_SIZE,
            )
            response_header = parse_device_config_response_header(
                raw_header
            )

            print(f"[CONFIG] Response header: {raw_header.hex()}")
            print(f"[CONFIG] Response command: {response_header.command}")
            print(f"[CONFIG] Response result: {response_header.result}")
            print(
                "[CONFIG] Configuration version: "
                f"{response_header.version}"
            )
            print(
                f"[CONFIG] Record count: {response_header.record_count}"
            )

            if response_header.result != 1001:
                raise PermissionError(
                    "Camera rejected the configuration request "
                    f"with result {response_header.result}."
                )
            if response_header.record_count <= 0:
                raise ValueError(
                    "Camera returned no configuration records."
                )

            records: list[DeviceConfigRecord] = []

            while len(records) < response_header.record_count:
                raw_record_header = _recv_exact(
                    sock,
                    DEVICE_CONFIG_RECORD_HEADER_SIZE,
                )
                payload_length = struct.unpack_from(
                    "<H",
                    raw_record_header,
                    3,
                )[0]

                if payload_length > MAX_RECORD_PAYLOAD_SIZE:
                    raise ValueError(
                        "Camera announced an unreasonable record "
                        f"payload size: {payload_length} bytes."
                    )

                payload = _recv_exact(sock, payload_length)
                record = parse_device_config_record(
                    raw_header=raw_record_header,
                    payload=payload,
                )
                records.append(record)

                print(
                    "[CONFIG] Record "
                    f"{len(records)}/{response_header.record_count}: "
                    f"index={record.index}, "
                    f"type={record.config_type} "
                    f"({record.config_name}), "
                    f"decoded={type(record.decoded).__name__}"
                )

                if record.index == response_header.record_count - 1:
                    break

    except socket.timeout as error:
        raise TimeoutError(
            "Timed out during the device-configuration exchange."
        ) from error
    except OSError as error:
        raise ConnectionError(
            "Device-configuration network failure for "
            f"{resolved_host}:{port}: {error}"
        ) from error

    return DeviceConfigExchange(
        host=resolved_host,
        port=port,
        request=request,
        response_header=response_header,
        records=tuple(records),
    )


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
