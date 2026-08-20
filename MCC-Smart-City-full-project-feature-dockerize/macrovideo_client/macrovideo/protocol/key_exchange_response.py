from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from ..crypto.base64utils import decode_base64
from ..crypto.curve25519 import Curve25519Session


@dataclass(frozen=True)
class KeyExchangeResult:
    sid: int
    exp: int
    camera_public_key: bytes
    shared_secret: bytes
    aes_key: bytes
    aes_iv: bytes
    raw_json: dict[str, Any]


def parse_key_exchange_response(
    payload: bytes,
    curve_session: Curve25519Session,
) -> KeyExchangeResult:
    try:
        text = payload.rstrip(b"\x00").decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(
            "Key-exchange response is not valid UTF-8 JSON."
        ) from error

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid key-exchange JSON: {error}"
        ) from error

    if not isinstance(document, dict):
        raise ValueError(
            "Key-exchange response root must be a JSON object."
        )

    data = document.get("data")

    if not isinstance(data, dict):
        raise ValueError(
            "Key-exchange response does not contain a data object."
        )

    sid = data.get("sid")
    exp = data.get("exp")
    encoded_camera_public_key = data.get("pubkC")

    if not isinstance(sid, int):
        raise ValueError(
            "Key-exchange response data.sid must be an integer."
        )

    if not 0 <= sid <= 0xFFFF:
        raise ValueError(
            f"Key-exchange SID must fit in 16 bits, received {sid}."
        )

    if not isinstance(exp, int):
        raise ValueError(
            "Key-exchange response data.exp must be an integer."
        )

    if not isinstance(encoded_camera_public_key, str):
        raise ValueError(
            "Key-exchange response data.pubkC must be a Base64 string."
        )

    camera_public_key = decode_base64(
        encoded_camera_public_key
    )

    if len(camera_public_key) != 32:
        raise ValueError(
            "Decoded camera Curve25519 public key must be 32 bytes, "
            f"received {len(camera_public_key)}."
        )

    shared_secret = curve_session.create_shared_secret(
        camera_public_key
    )

    aes_key, aes_iv = curve_session.derive_aes_material()

    return KeyExchangeResult(
        sid=sid,
        exp=exp,
        camera_public_key=camera_public_key,
        shared_secret=shared_secret,
        aes_key=aes_key,
        aes_iv=aes_iv,
        raw_json=document,
    )