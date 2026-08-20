from __future__ import annotations


# Legacy login protocol
LOGIN_REQUEST = 1167
LOGIN_RESPONSE = 1168
LOGIN_PACKET_SIZE = 256

LOGIN_SUCCESS_CODE = 1001


# V3 common packet protocol
COMMON_JSON_COMMAND = 0x38030818
MEDIA_PACKET_COMMAND = 0x38030820
COMMON_HEADER_SIZE = 16


# V3 JSON method IDs
KEY_EXCHANGE_REQUEST = 0x30108
KEY_EXCHANGE_RESPONSE = 0x30109

KEEPALIVE_REQUEST = 0x30200

PREVIEW_REQUEST = 0x30202
PREVIEW_RESPONSE = 0x30203
MEDIA_INFO_NOTIFICATION = 0x30204


# Security modes
SECURITY_PLAINTEXT = 0
SECURITY_AES_ECB = 1
SECURITY_AES_CBC = 2


# Stream quality values sent in JSON
QUALITY_SD = 1
QUALITY_HD = 2


# Crypto sizes
AES_KEY_SIZE = 16
AES_IV_SIZE = 16
CURVE25519_KEY_SIZE = 32


# Networking
DEFAULT_CAMERA_PORT = 8800
DEFAULT_CONNECT_TIMEOUT = 5.0
DEFAULT_READ_TIMEOUT = 8.0
MAX_PAYLOAD_SIZE = 16 * 1024 * 1024


# LAN-password key exchange
LAN_PASSWORD_REQUEST = 0x30106       # 196870
LAN_PASSWORD_RESPONSE = 0x30107      # 196871

LAN_PASSWORD_SUCCESS = 1000
LAN_PASSWORD_INCORRECT = 1119

# Exact fixed 32-byte material from LoginHelper.f17743e.
LAN_BOOTSTRAP_MATERIAL = bytes(
    [
        54,
        58,
        229,
        40,
        22,
        56,
        207,
        132,
        150,
        154,
        99,
        78,
        159,
        150,
        106,
        152,
        181,
        115,
        209,
        255,
        233,
        55,
        178,
        119,
        209,
        241,
        214,
        43,
        56,
        116,
        138,
        229,
    ]
)