from __future__ import annotations

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes,
)


AES_BLOCK_SIZE_BYTES = 16
AES_BLOCK_SIZE_BITS = AES_BLOCK_SIZE_BYTES * 8


def _validate_key(key: bytes) -> None:
    if len(key) != 16:
        raise ValueError(
            f"V380 AES key must be 16 bytes, received {len(key)}."
        )


def _validate_iv(iv: bytes) -> None:
    if len(iv) != 16:
        raise ValueError(
            f"V380 AES IV must be 16 bytes, received {len(iv)}."
        )


def pkcs7_pad(data: bytes) -> bytes:
    padder = padding.PKCS7(AES_BLOCK_SIZE_BITS).padder()
    return padder.update(data) + padder.finalize()


def pkcs7_unpad(data: bytes) -> bytes:
    unpadder = padding.PKCS7(AES_BLOCK_SIZE_BITS).unpadder()
    return unpadder.update(data) + unpadder.finalize()


def encrypt_ecb(plaintext: bytes, key: bytes) -> bytes:
    _validate_key(key)

    encryptor = Cipher(
        algorithms.AES(key),
        modes.ECB(),
    ).encryptor()

    padded = pkcs7_pad(plaintext)
    return encryptor.update(padded) + encryptor.finalize()


def decrypt_ecb(ciphertext: bytes, key: bytes) -> bytes:
    _validate_key(key)

    if len(ciphertext) % AES_BLOCK_SIZE_BYTES != 0:
        raise ValueError("ECB ciphertext is not block-aligned.")

    decryptor = Cipher(
        algorithms.AES(key),
        modes.ECB(),
    ).decryptor()

    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return pkcs7_unpad(padded)


def encrypt_cbc(
    plaintext: bytes,
    key: bytes,
    iv: bytes,
) -> bytes:
    _validate_key(key)
    _validate_iv(iv)

    encryptor = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
    ).encryptor()

    padded = pkcs7_pad(plaintext)
    return encryptor.update(padded) + encryptor.finalize()


def decrypt_cbc(
    ciphertext: bytes,
    key: bytes,
    iv: bytes,
) -> bytes:
    _validate_key(key)
    _validate_iv(iv)

    if len(ciphertext) % AES_BLOCK_SIZE_BYTES != 0:
        raise ValueError("CBC ciphertext is not block-aligned.")

    decryptor = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
    ).decryptor()

    padded = decryptor.update(ciphertext) + decryptor.finalize()
    return pkcs7_unpad(padded)