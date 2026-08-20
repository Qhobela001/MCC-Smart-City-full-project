from __future__ import annotations

import base64
import binascii


def encode_base64(data: bytes) -> str:
    """Android Base64.NO_WRAP equivalent."""

    return base64.b64encode(data).decode("ascii")


def decode_base64(value: str) -> bytes:
    try:
        return base64.b64decode(
            value,
            validate=True,
        )
    except (binascii.Error, ValueError) as error:
        raise ValueError("Invalid Base64 value.") from error