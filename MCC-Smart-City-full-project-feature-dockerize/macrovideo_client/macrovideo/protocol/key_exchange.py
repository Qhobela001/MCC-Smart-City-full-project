from __future__ import annotations

import uuid as uuid_module
from dataclasses import dataclass

from ..crypto.base64utils import encode_base64
from ..crypto.curve25519 import (
    Curve25519KeyPair,
    Curve25519Session,
)
from ..crypto.hashing import sha256
from ..utils import random_sequence


KEY_EXCHANGE_REQUEST_METHOD = 0x30108
KEY_EXCHANGE_RESPONSE_METHOD = 0x30109


@dataclass(frozen=True)
class KeyExchangeRequestData:
    request_id: int
    client_uuid: str
    client_seed: bytes
    client_public_key: bytes
    client_public_key_hash: bytes
    client_public_value: str
    params: dict[str, str]


class KeyExchangeRequest:
    """Prepare the V380 V3 key-exchange request parameters."""

    def __init__(
        self,
        curve_session: Curve25519Session | None = None,
    ) -> None:
        self.curve_session = (
            curve_session
            if curve_session is not None
            else Curve25519Session()
        )

    def build(
        self,
        client_uuid: str | None = None,
        request_id: int | None = None,
    ) -> KeyExchangeRequestData:
        key_pair: Curve25519KeyPair = (
            self.curve_session.generate()
        )

        resolved_uuid = (
            client_uuid
            if client_uuid is not None
            else str(uuid_module.uuid4())
        )

        resolved_request_id = (
            request_id
            if request_id is not None
            else random_sequence()
        )

        public_key_hash = sha256(key_pair.public_key)
        client_public_value = encode_base64(public_key_hash)

        params = {
            "uuid": resolved_uuid,
            "cS": client_public_value,
        }

        return KeyExchangeRequestData(
            request_id=resolved_request_id,
            client_uuid=resolved_uuid,
            client_seed=key_pair.seed,
            client_public_key=key_pair.public_key,
            client_public_key_hash=public_key_hash,
            client_public_value=client_public_value,
            params=params,
        )