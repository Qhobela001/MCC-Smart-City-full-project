from __future__ import annotations

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


LOGIN_ENCRYPTION_KEY = b"1234567890123456"
AES_BLOCK_SIZE = AES.block_size


def encrypt_login_password(
    password: str,
    *,
    key: bytes = LOGIN_ENCRYPTION_KEY,
) -> bytes:
    """
    Reproduce the Android account-login password encryption:

        AES/ECB/PKCS5Padding

    Java's PKCS5Padding implementation for AES is equivalent to
    PKCS#7 padding using AES's 16-byte block size.
    """

    if not password:
        raise ValueError(
            "V380 account password cannot be empty."
        )

    if len(key) not in {16, 24, 32}:
        raise ValueError(
            "AES key must contain 16, 24, or 32 bytes."
        )

    plaintext = password.encode("utf-8")

    cipher = AES.new(
        key,
        AES.MODE_ECB,
    )

    return cipher.encrypt(
        pad(
            plaintext,
            AES_BLOCK_SIZE,
            style="pkcs7",
        )
    )


def encrypt_login_password_hex(
    password: str,
    *,
    key: bytes = LOGIN_ENCRYPTION_KEY,
) -> str:
    """
    Encrypt the account password and return lowercase hexadecimal,
    matching GlobalDefines.byte2Hex(...).
    """

    encrypted = encrypt_login_password(
        password,
        key=key,
    )

    return encrypted.hex()