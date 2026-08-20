from __future__ import annotations

import hashlib
import hmac
import struct
import time

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad


PROTOCOL_VERSION = 2
STATIC_MARKER = "2025&N+E+W"

TOTP_STEP_SECONDS = 30
TOTP_DIGITS = 6

HEADER_SIZE = 8


def compact_topic(identifier: str) -> str:
    """
    Convert the MQTT identity format used in a topic into the compact
    identity used for AES key derivation.

    Examples:
        CID105848032 -> D105848032
        UID123456    -> U123456
    """

    if identifier.startswith("CID") and len(identifier) > 3:
        return "D" + identifier[3:]

    if identifier.startswith("UID") and len(identifier) > 3:
        return "U" + identifier[3:]

    return "MUL"


def generate_totp(
    key: bytes,
    timestamp_seconds: int,
    *,
    step_seconds: int = TOTP_STEP_SECONDS,
    digits: int = TOTP_DIGITS,
) -> int:
    """
    Reproduce MessagePayloadTools.generateTOTP().

    Java calculates:

        counter = unix_time_seconds / 30
        HMAC-SHA1(key, big-endian 8-byte counter)
        dynamic truncation
        result modulo 10^6
    """

    if not key:
        raise ValueError("TOTP key cannot be empty.")

    if timestamp_seconds < 0:
        raise ValueError(
            "TOTP timestamp cannot be negative."
        )

    if step_seconds <= 0:
        raise ValueError(
            "TOTP step must be greater than zero."
        )

    if digits <= 0:
        raise ValueError(
            "TOTP digit count must be greater than zero."
        )

    counter = timestamp_seconds // step_seconds

    counter_bytes = struct.pack(
        ">Q",
        counter,
    )

    digest = hmac.new(
        key,
        counter_bytes,
        hashlib.sha1,
    ).digest()

    offset = digest[-1] & 0x0F

    truncated = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )

    return truncated % (10**digits)


def derive_totp_seed(
    *,
    rand_key: str,
    source: str,
    destination: str,
) -> bytes:
    """
    Java equivalent:

        SHA1(
            randKey
            + "2025&N+E+W"
            + sourceNumber
            + "="
            + destinationNumber
        )
    """

    if not rand_key:
        raise ValueError(
            "Device randKey cannot be empty."
        )

    _validate_identifier(source, "source")
    _validate_identifier(destination, "destination")

    source_number = source[3:]
    destination_number = destination[3:]

    seed_text = (
        rand_key
        + STATIC_MARKER
        + source_number
        + "="
        + destination_number
    )

    return hashlib.sha1(
        seed_text.encode("utf-8")
    ).digest()


def derive_aes_key(
    *,
    rand_key: str,
    source: str,
    destination: str,
    totp: int,
) -> bytes:
    """
    Java equivalent:

        MD5(
            randKey
            + compactSource
            + compactDestination
            + decimalTOTP
        )

    The resulting 16 bytes are used as both the AES key and IV.
    """

    if not rand_key:
        raise ValueError(
            "Device randKey cannot be empty."
        )

    _validate_identifier(source, "source")
    _validate_identifier(destination, "destination")

    material = (
        rand_key
        + compact_topic(source)
        + compact_topic(destination)
        + str(totp)
    )

    return hashlib.md5(
        material.encode("utf-8")
    ).digest()


def build_message_payload(
    *,
    source: str,
    destination: str,
    rand_key: str,
    json_text: str,
    flag: int = 0,
    properties: bytes = b"",
    timestamp_seconds: int | None = None,
) -> bytes:
    """
    Reproduce MessagePayloadTools.newMessageLoad().

    Packet layout:

        byte 0      protocol version, always 2
        byte 1      flags
        bytes 2-5   six-digit TOTP as uint32 little-endian
        bytes 6-7   properties length as uint16 little-endian
        bytes 8...  AES-CBC encrypted JSON
        final bytes optional property block

    The Java wake-up calls currently use an empty property block.
    """

    _validate_identifier(source, "source")
    _validate_identifier(destination, "destination")

    if not rand_key:
        raise ValueError(
            "Device randKey cannot be empty."
        )

    if not isinstance(json_text, str):
        raise TypeError(
            "json_text must be a string."
        )

    if not 0 <= flag <= 0xFF:
        raise ValueError(
            "MQTT payload flag must fit in one byte."
        )

    if len(properties) > 0xFFFF:
        raise ValueError(
            "MQTT properties block is too large."
        )

    timestamp = (
        int(time.time())
        if timestamp_seconds is None
        else timestamp_seconds
    )

    totp_seed = derive_totp_seed(
        rand_key=rand_key,
        source=source,
        destination=destination,
    )

    totp = generate_totp(
        totp_seed,
        timestamp,
    )

    aes_key = derive_aes_key(
        rand_key=rand_key,
        source=source,
        destination=destination,
        totp=totp,
    )

    cipher = AES.new(
        aes_key,
        AES.MODE_CBC,
        iv=aes_key,
    )

    encrypted_json = cipher.encrypt(
        pad(
            json_text.encode("utf-8"),
            AES.block_size,
        )
    )

    header = b"".join(
        (
            bytes((PROTOCOL_VERSION,)),
            bytes((flag,)),
            struct.pack("<I", totp),
            struct.pack("<H", len(properties)),
        )
    )

    return (
        header
        + encrypted_json
        + properties
    )


def decrypt_message_payload(
    *,
    payload: bytes,
    mqtt_topic: str,
    rand_key: str,
) -> str:
    """
    Reproduce MessagePayloadTools.DecryptDeviceCipherText().

    The incoming MQTT topic determines the source and destination order.
    The first two CID/UID topic segments are used for AES derivation.
    """

    if len(payload) < HEADER_SIZE:
        raise ValueError(
            "MQTT payload is shorter than its 8-byte header."
        )

    if not rand_key:
        raise ValueError(
            "Device randKey cannot be empty."
        )

    protocol_version = payload[0]

    if protocol_version != PROTOCOL_VERSION:
        raise ValueError(
            "Unsupported MQTT payload protocol version: "
            f"{protocol_version}."
        )

    totp = struct.unpack_from(
        "<I",
        payload,
        2,
    )[0]

    # The Java decoder reconstructs this field as big-endian, although
    # its encoder writes it little-endian. Current wake-up packets use
    # zero property bytes, so the byte order does not affect them.
    properties_length_be = struct.unpack_from(
        ">H",
        payload,
        6,
    )[0]

    properties_length_le = struct.unpack_from(
        "<H",
        payload,
        6,
    )[0]

    properties_length = _resolve_properties_length(
        payload_length=len(payload),
        big_endian_value=properties_length_be,
        little_endian_value=properties_length_le,
    )

    identifiers = _extract_identifiers_from_topic(
        mqtt_topic
    )

    if len(identifiers) < 2:
        raise ValueError(
            "MQTT response topic does not contain two "
            "CID/UID identifiers."
        )

    source = identifiers[0]
    destination = identifiers[1]

    encrypted_end = (
        len(payload) - properties_length
    )

    if encrypted_end <= HEADER_SIZE:
        raise ValueError(
            "MQTT encrypted payload is empty or malformed."
        )

    ciphertext = payload[
        HEADER_SIZE:encrypted_end
    ]

    if len(ciphertext) % AES.block_size != 0:
        raise ValueError(
            "MQTT encrypted payload is not aligned "
            "to the AES block size."
        )

    aes_key = derive_aes_key(
        rand_key=rand_key,
        source=source,
        destination=destination,
        totp=totp,
    )

    cipher = AES.new(
        aes_key,
        AES.MODE_CBC,
        iv=aes_key,
    )

    plaintext = unpad(
        cipher.decrypt(ciphertext),
        AES.block_size,
    )

    return plaintext.decode("utf-8")


def extract_payload_totp(
    payload: bytes,
) -> int:
    if len(payload) < HEADER_SIZE:
        raise ValueError(
            "MQTT payload is shorter than its header."
        )

    return struct.unpack_from(
        "<I",
        payload,
        2,
    )[0]


def _extract_identifiers_from_topic(
    mqtt_topic: str,
) -> list[str]:
    identifiers: list[str] = []

    for segment in mqtt_topic.split("/"):
        if (
            segment.startswith(("CID", "UID"))
            and len(segment) > 3
        ):
            identifiers.append(segment)

    return identifiers


def _resolve_properties_length(
    *,
    payload_length: int,
    big_endian_value: int,
    little_endian_value: int,
) -> int:
    for candidate in (
        big_endian_value,
        little_endian_value,
    ):
        encrypted_size = (
            payload_length
            - HEADER_SIZE
            - candidate
        )

        if (
            candidate <= payload_length - HEADER_SIZE
            and encrypted_size > 0
            and encrypted_size % AES.block_size == 0
        ):
            return candidate

    raise ValueError(
        "Could not determine the MQTT properties length."
    )


def _validate_identifier(
    identifier: str,
    field_name: str,
) -> None:
    if not isinstance(identifier, str):
        raise TypeError(
            f"{field_name} must be a string."
        )

    if not identifier.startswith(
        ("CID", "UID")
    ):
        raise ValueError(
            f"{field_name} must begin with CID or UID."
        )

    if len(identifier) <= 3:
        raise ValueError(
            f"{field_name} does not contain an ID."
        )