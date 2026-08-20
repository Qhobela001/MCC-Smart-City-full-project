from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import time
from dataclasses import dataclass
from typing import Any

from ..constants import (
    COMMON_HEADER_SIZE,
    COMMON_JSON_COMMAND,
    KEY_EXCHANGE_REQUEST,
    MAX_PAYLOAD_SIZE,
    SECURITY_PLAINTEXT,
)
from ..crypto.curve25519 import Curve25519Session
from ..packet import CommonPacket, parse_common_header
from ..protocol.key_exchange_response import (
    KeyExchangeResult,
    parse_key_exchange_response,
)
from ..utils import random_sequence


@dataclass(frozen=True)
class MqSocketKeyExchangeRequest:
    request_id: int
    client_uuid: str
    client_public_key_hash: bytes
    client_public_value: str
    timestamp: int
    json_document: dict[str, Any]
    json_payload: bytes
    packet: bytes


@dataclass(frozen=True)
class MqSocketKeyExchangeResponse:
    header: CommonPacket
    payload_size: int
    payload: bytes
    key_exchange: KeyExchangeResult


@dataclass(frozen=True)
class MqSocketKeyExchangeResult:
    host: str
    port: int
    request: MqSocketKeyExchangeRequest
    response: MqSocketKeyExchangeResponse


_HEADER = struct.Struct("<IBBBBII")


def build_mq_socket_key_exchange_request(
    *,
    client_uuid: str,
    client_public_key: bytes,
    request_id: int | None = None,
    timestamp: int | None = None,
    is_mr: bool = False,
) -> MqSocketKeyExchangeRequest:
    """
    Build the direct pver=2 TCP key-exchange packet.

    Important protocol detail:
    Android's common JSON header uses Unix time in SECONDS. The earlier
    implementation incorrectly sent a 13-digit millisecond timestamp,
    which causes this camera to close the TCP socket without replying.
    """

    resolved_uuid = client_uuid.strip()

    if not resolved_uuid:
        raise ValueError(
            "Client UUID cannot be empty."
        )

    if len(client_public_key) != 32:
        raise ValueError(
            "Client Curve25519 public key must be exactly 32 bytes."
        )

    resolved_request_id = (
        random_sequence()
        if request_id is None
        else request_id
    )

    if not 1 <= resolved_request_id <= 0x7FFFFFFF:
        raise ValueError(
            "Request ID must be between 1 and 0x7fffffff."
        )

    resolved_timestamp = (
        int(time.time())
        if timestamp is None
        else timestamp
    )

    if not 0 <= resolved_timestamp <= 0x7FFFFFFF:
        raise ValueError(
            "Timestamp must fit in a positive signed 32-bit integer."
        )

    public_key_hash = hashlib.sha256(
        client_public_key
    ).digest()

    client_public_value = base64.b64encode(
        public_key_hash
    ).decode("ascii")

    params = {
        "uuid": resolved_uuid,
        "cS": client_public_value,
    }

    # Match the field order already used by build_iotc_request() and
    # observed in the Android/native packet output.
    document: dict[str, Any] = {
        "id": resolved_request_id,
        "chn": 1,
        "method_id": KEY_EXCHANGE_REQUEST,
        "ts": resolved_timestamp,
        "params": params,
    }

    json_text = json.dumps(
        document,
        separators=(",", ":"),
        ensure_ascii=False,
    ).replace("\\", "")

    payload = json_text.encode("utf-8")

    if len(payload) > MAX_PAYLOAD_SIZE:
        raise ValueError(
            "Key-exchange payload is too large: "
            f"{len(payload)} bytes."
        )

    header = _HEADER.pack(
        COMMON_JSON_COMMAND,
        1,
        SECURITY_PLAINTEXT,
        0,
        0,
        0,
        len(payload),
    )

    if len(header) != COMMON_HEADER_SIZE:
        raise AssertionError(
            "Common packet header is not 16 bytes."
        )

    if is_mr:
        forward = bytearray(64)
        struct.pack_into("<I", forward, 0, 1200)
        struct.pack_into(
            "<I",
            forward,
            4,
            len(header) + len(payload),
        )
        packet = bytes(forward) + header + payload
    else:
        packet = header + payload

    return MqSocketKeyExchangeRequest(
        request_id=resolved_request_id,
        client_uuid=resolved_uuid,
        client_public_key_hash=public_key_hash,
        client_public_value=client_public_value,
        timestamp=resolved_timestamp,
        json_document=document,
        json_payload=payload,
        packet=packet,
    )


def open_mq_socket(
    *,
    host: str,
    port: int,
    connect_timeout: float = 8.0,
    read_timeout: float = 18.0,
) -> socket.socket:
    resolved_host = host.strip()

    if not resolved_host:
        raise ValueError(
            "Camera host cannot be empty."
        )

    if not 1 <= port <= 65535:
        raise ValueError(
            "Camera TCP port must be between 1 and 65535."
        )

    try:
        sock = socket.create_connection(
            (resolved_host, port),
            timeout=connect_timeout,
        )
        sock.settimeout(read_timeout)
        return sock
    except OSError as error:
        raise ConnectionError(
            "Could not open camera TCP socket "
            f"to {resolved_host}:{port}: {error}"
        ) from error


def perform_mq_socket_key_exchange_on_socket(
    *,
    sock: socket.socket,
    host: str,
    port: int,
    client_uuid: str,
    client_public_key: bytes,
    curve_session: Curve25519Session,
    request_id: int | None = None,
    timestamp: int | None = None,
) -> MqSocketKeyExchangeResult:
    request = build_mq_socket_key_exchange_request(
        client_uuid=client_uuid,
        client_public_key=client_public_key,
        request_id=request_id,
        timestamp=timestamp,
        is_mr=False,
    )

    try:
        print(f"[TCP] Connected to {host}:{port}")
        print(f"[TCP] Request ID: {request.request_id}")
        print(f"[TCP] Timestamp: {request.timestamp}")
        print(
            "[TCP] Outgoing JSON: "
            f"{request.json_payload.decode('utf-8')}"
        )
        print(
            "[TCP] Header: "
            f"{request.packet[:16].hex()}"
        )
        print(
            "[TCP] Packet size: "
            f"{len(request.packet)} bytes"
        )

        sock.sendall(request.packet)

        print(
            "[TCP] Packet sent; waiting for "
            "16-byte response header..."
        )

        response_header_bytes = _recv_exact(
            sock,
            COMMON_HEADER_SIZE,
        )

        response_header = parse_common_header(
            response_header_bytes
        )

        payload_size = struct.unpack_from(
            "<I",
            response_header_bytes,
            12,
        )[0]

        print(
            "[TCP] Response header: "
            f"{response_header_bytes.hex()}"
        )
        print(
            "[TCP] Response command: "
            f"0x{response_header.command:08x}"
        )
        print(
            "[TCP] Response security mode: "
            f"{response_header.security_mode}"
        )
        print(
            "[TCP] Response payload size: "
            f"{payload_size}"
        )

        if response_header.command != COMMON_JSON_COMMAND:
            raise ValueError(
                "Unexpected TCP response command: "
                f"0x{response_header.command:08x}; "
                "expected "
                f"0x{COMMON_JSON_COMMAND:08x}."
            )

        if payload_size <= 0:
            raise ValueError(
                "Camera returned an empty "
                "key-exchange payload."
            )

        if payload_size > MAX_PAYLOAD_SIZE:
            raise ValueError(
                "Camera announced an unreasonable "
                "key-exchange payload: "
                f"{payload_size} bytes."
            )

        payload = _recv_exact(
            sock,
            payload_size,
        )

    except socket.timeout as error:
        raise TimeoutError(
            "Timed out during the camera TCP "
            "key exchange."
        ) from error
    except OSError as error:
        raise ConnectionError(
            "Could not complete camera TCP key "
            f"exchange with {host}:{port}: {error}"
        ) from error

    key_exchange = _parse_response_payload(
        payload,
        curve_session,
    )

    response = MqSocketKeyExchangeResponse(
        header=response_header,
        payload_size=payload_size,
        payload=payload,
        key_exchange=key_exchange,
    )

    return MqSocketKeyExchangeResult(
        host=host,
        port=port,
        request=request,
        response=response,
    )


def perform_mq_socket_key_exchange(
    *,
    host: str,
    port: int,
    client_uuid: str,
    client_public_key: bytes,
    curve_session: Curve25519Session,
    connect_timeout: float = 8.0,
    read_timeout: float = 18.0,
    request_id: int | None = None,
    timestamp: int | None = None,
) -> MqSocketKeyExchangeResult:
    sock = open_mq_socket(
        host=host,
        port=port,
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )

    try:
        return perform_mq_socket_key_exchange_on_socket(
            sock=sock,
            host=host,
            port=port,
            client_uuid=client_uuid,
            client_public_key=client_public_key,
            curve_session=curve_session,
            request_id=request_id,
            timestamp=timestamp,
        )
    finally:
        sock.close()

def _parse_response_payload(
    payload: bytes,
    curve_session: Curve25519Session,
) -> KeyExchangeResult:
    try:
        text = payload.rstrip(
            b"\x00"
        ).decode("utf-8")

        document = json.loads(
            text
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise ValueError(
            "Camera TCP key-exchange payload is "
            "not valid UTF-8 JSON: "
            f"{payload[:128].hex()}"
        ) from error

    if not isinstance(
        document,
        dict,
    ):
        raise ValueError(
            "Camera key-exchange JSON root "
            "must be an object."
        )

    data = document.get("data")

    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Camera key-exchange response does "
            "not contain a data object: "
            f"{document}"
        )

    if (
        "pubkC" not in data
        and isinstance(
            data.get("pubKC"),
            str,
        )
    ):
        normalized = dict(
            document
        )
        normalized_data = dict(
            data
        )
        normalized_data["pubkC"] = (
            normalized_data["pubKC"]
        )
        normalized["data"] = (
            normalized_data
        )

        payload = json.dumps(
            normalized,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    return parse_key_exchange_response(
        payload,
        curve_session,
    )


def _recv_exact(
    sock: socket.socket,
    size: int,
) -> bytes:
    if size < 0:
        raise ValueError(
            "Receive size cannot be negative."
        )

    buffer = bytearray()

    while len(buffer) < size:
        chunk = sock.recv(
            size - len(buffer)
        )

        if not chunk:
            raise ConnectionError(
                "Camera closed the TCP connection "
                f"after {len(buffer)} of {size} "
                "expected bytes."
            )

        buffer.extend(
            chunk
        )

    return bytes(
        buffer
    )
