from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from ..constants import (
    COMMON_JSON_COMMAND,
    SECURITY_AES_CBC,
    SECURITY_AES_ECB,
    SECURITY_PLAINTEXT,
)
from ..crypto.aes import encrypt_cbc, encrypt_ecb
from ..packet import build_common_packet


@dataclass(frozen=True)
class IotcRequest:
    request_id: int
    channel: int
    method_id: int
    timestamp: int
    params: dict[str, Any]
    security_mode: int
    sid: int
    raw_json: bytes
    wire_payload: bytes
    packet: bytes


def build_iotc_request(
    *,
    request_id: int,
    channel: int,
    method_id: int,
    params: dict[str, Any],
    security_mode: int = SECURITY_PLAINTEXT,
    sid: int = 0,
    key: bytes | None = None,
    iv: bytes | None = None,
    timestamp: int | None = None,
) -> IotcRequest:
    resolved_timestamp = (
        int(time.time())
        if timestamp is None
        else timestamp
    )

    body = {
        "id": request_id,
        "chn": channel,
        "method_id": method_id,
        "ts": resolved_timestamp,
        "params": params,
    }

    raw_json = json.dumps(
        body,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    if security_mode == SECURITY_PLAINTEXT:
        wire_payload = raw_json

    elif security_mode == SECURITY_AES_ECB:
        if key is None:
            raise ValueError(
                "AES-ECB request requires a key."
            )

        wire_payload = encrypt_ecb(
            raw_json,
            key,
        )

    elif security_mode == SECURITY_AES_CBC:
        if key is None or iv is None:
            raise ValueError(
                "AES-CBC request requires both key and IV."
            )

        wire_payload = encrypt_cbc(
            raw_json,
            key,
            iv,
        )

    else:
        raise ValueError(
            f"Unsupported security mode: {security_mode}"
        )

    packet = build_common_packet(
        wire_payload,
        command=COMMON_JSON_COMMAND,
        version=1,
        security_mode=security_mode,
        field_6=sid & 0xFF,
        field_7=0,
        reserved=0,
    )

    return IotcRequest(
        request_id=request_id,
        channel=channel,
        method_id=method_id,
        timestamp=resolved_timestamp,
        params=params,
        security_mode=security_mode,
        sid=sid,
        raw_json=raw_json,
        wire_payload=wire_payload,
        packet=packet,
    )