from __future__ import annotations

from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)

from ..utils import create_seed


@dataclass(frozen=True)
class Curve25519KeyPair:
    seed: bytes
    public_key: bytes


class Curve25519Session:
    """Curve25519/X25519 session used by the V380 V3 protocol."""

    def __init__(self) -> None:
        self._private_key: X25519PrivateKey | None = None
        self.seed: bytes | None = None
        self.public_key: bytes | None = None
        self.shared_secret: bytes | None = None

    @property
    def key_pair(self) -> Curve25519KeyPair:
        """
        Return the currently generated client key material.

        This is used by the MQTT wake-up flow and later by the
        V3 key-exchange flow so both stages can reuse the same
        Curve25519 session.
        """

        if self.seed is None or self.public_key is None:
            raise RuntimeError(
                "Curve25519 key pair has not been generated yet."
            )

        return Curve25519KeyPair(
            seed=self.seed,
            public_key=self.public_key,
        )

    def generate(self) -> Curve25519KeyPair:
        """
        Reproduce:

            seed = Functions.getCharAndNumr(32).getBytes()
            curve25519_CalculatePublicKey(public_key, seed)
        """

        seed = create_seed()

        if len(seed) != 32:
            raise ValueError(
                f"Curve25519 seed must be 32 bytes, received {len(seed)}."
            )

        private_key = X25519PrivateKey.from_private_bytes(seed)

        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

        self.seed = seed
        self._private_key = private_key
        self.public_key = public_key
        self.shared_secret = None

        return Curve25519KeyPair(
            seed=seed,
            public_key=public_key,
        )

    def create_shared_secret(
        self,
        camera_public_key: bytes,
    ) -> bytes:
        """
        Reproduce:

            curve25519_CreateSharedKey(
                output,
                client_seed,
                camera_public_key,
            )
        """

        if self._private_key is None:
            raise RuntimeError(
                "Generate the client Curve25519 key pair first."
            )

        if len(camera_public_key) != 32:
            raise ValueError(
                "Camera Curve25519 public key must be exactly 32 bytes."
            )

        remote_public_key = X25519PublicKey.from_public_bytes(
            camera_public_key
        )

        shared_secret = self._private_key.exchange(
            remote_public_key
        )

        if len(shared_secret) != 32:
            raise RuntimeError(
                "Curve25519 did not produce a 32-byte shared secret."
            )

        self.shared_secret = shared_secret

        return shared_secret

    def derive_aes_material(self) -> tuple[bytes, bytes]:
        """
        Native layout:

            shared_secret[0:16]  -> AES-128 key
            shared_secret[16:32] -> AES-CBC IV
        """

        if self.shared_secret is None:
            raise RuntimeError(
                "Create the Curve25519 shared secret first."
            )

        return (
            self.shared_secret[:16],
            self.shared_secret[16:32],
        )