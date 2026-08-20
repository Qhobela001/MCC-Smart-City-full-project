
from __future__ import annotations
from dataclasses import dataclass
from Crypto.Cipher import AES

_FIXED_SUFFIX = bytes.fromhex("5c79142c46238161f00d8082")

@dataclass(frozen=True)
class LegacyMediaKey:
    login_handle: int
    key: bytes

def derive_legacy_media_key(login_handle: int) -> LegacyMediaKey:
    if login_handle <= 0:
        raise ValueError("Legacy login handle must be positive.")
    key = login_handle.to_bytes(4, "little", signed=False) + _FIXED_SUFFIX
    if len(key) != 16:
        raise AssertionError("AES key must be 16 bytes.")
    return LegacyMediaKey(login_handle=login_handle, key=key)

def decrypt_media_payload_pre_2k(
    payload: bytes,
    *,
    login_handle: int,
    special_media: bool = False,
) -> bytes:
    if not payload:
        return b""
    aligned = len(payload) - (len(payload) % 16)
    decrypt_length = aligned if special_media else min(aligned, 2048)
    if decrypt_length <= 0:
        return payload

    key = derive_legacy_media_key(login_handle).key
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.decrypt(payload[:decrypt_length]) + payload[decrypt_length:]
