from __future__ import annotations

import json
import sys
from pprint import pprint

from macrovideo.config import CameraConfig
from macrovideo.constants import (
    COMMON_JSON_COMMAND,
    KEY_EXCHANGE_REQUEST,
    KEY_EXCHANGE_RESPONSE,
    SECURITY_PLAINTEXT,
)
from macrovideo.protocol.iotc import build_iotc_request
from macrovideo.protocol.key_exchange import KeyExchangeRequest
from macrovideo.protocol.key_exchange_response import (
    parse_key_exchange_response,
)
from macrovideo.protocol.login import login
from macrovideo.socket_client import CameraSocket


CAMERA_IP = "192.2.42.100"
CAMERA_PORT = 8800

DEVICE_ID = 105848032
V3_CHANNEL = DEVICE_ID + 1

USERNAME = "admin"
PASSWORD = "Password@9"


def decode_json_payload(
    payload: bytes,
) -> dict[str, object]:
    text = payload.rstrip(b"\x00").decode("utf-8")

    print("\nRaw response JSON:")
    print(text)

    document = json.loads(text)

    if not isinstance(document, dict):
        raise ValueError(
            "Camera response root is not a JSON object."
        )

    return document


def read_integer(
    document: dict[str, object],
    name: str,
) -> int | None:
    value = document.get(name)

    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value

    return None


def main() -> int:
    print("=" * 72)
    print("V380 LOGIN + V3 KEY-EXCHANGE TEST")
    print("=" * 72)

    print(f"Camera: {CAMERA_IP}:{CAMERA_PORT}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"V3 chn value: {V3_CHANNEL}")

    config = CameraConfig(
        ip=CAMERA_IP,
        port=CAMERA_PORT,
        username=USERNAME,
        password=PASSWORD,
        device_id=DEVICE_ID,
        timeout=10.0,
    )

    key_exchange_builder = KeyExchangeRequest()
    key_exchange_data = key_exchange_builder.build()

    request = build_iotc_request(
        request_id=key_exchange_data.request_id,
        channel=V3_CHANNEL,
        method_id=KEY_EXCHANGE_REQUEST,
        params=key_exchange_data.params,
        security_mode=SECURITY_PLAINTEXT,
        sid=0,
    )

    print("\nKey-exchange parameters")
    print(f"UUID: {key_exchange_data.client_uuid}")
    print(f"Request ID: {key_exchange_data.request_id}")
    print(f"Seed: {key_exchange_data.client_seed!r}")

    print(
        "Public key: "
        f"{key_exchange_data.client_public_key.hex()}"
    )

    print(
        "SHA-256(public key): "
        f"{key_exchange_data.client_public_key_hash.hex()}"
    )

    print(
        f"cS: {key_exchange_data.client_public_value}"
    )

    print("\nOutgoing key-exchange JSON")
    print(request.raw_json.decode("utf-8"))

    print("\nOutgoing packet")
    print(f"Packet size: {len(request.packet)} bytes")
    print(f"Header: {request.packet[:16].hex()}")
    print(f"Payload: {request.packet[16:].hex()}")

    try:
        print("\n" + "=" * 72)
        print("STEP 1: OPEN AND KEEP LEGACY LOGIN SESSION")
        print("=" * 72)

        with CameraSocket(config) as login_camera:
            print("[+] Login TCP connection established")

            session = login(
                login_camera,
                device_id=DEVICE_ID,
                username=USERNAME,
                password=PASSWORD,
            )

            print("\n" + "=" * 72)
            print("LOGIN SUCCEEDED")
            print("=" * 72)

            print(f"Handle: {session.handle}")
            print(f"Session token: {session.session_token}")
            print(f"Protocol version: {session.version}")
            print(f"Device type: {session.device_type}")
            print(f"Camera type: {session.camera_type}")
            print(f"LAN flag: {session.lan_flag}")
            print(f"Domain: {session.domain or '<empty>'}")
            print(
                "LAN address: "
                f"{session.lan_address or '<empty>'}"
            )
            print(f"Channel count: {session.channel_count}")

            print(
                "[+] The authenticated login socket "
                "will remain open."
            )

            print("\n" + "=" * 72)
            print("STEP 2: OPEN SEPARATE V3 STREAM SOCKET")
            print("=" * 72)

            with CameraSocket(config) as v3_camera:
                print("[+] V3 TCP connection established")

                print(
                    "[>] Sending plaintext "
                    "key-exchange request..."
                )

                v3_camera.send_all(request.packet)

                print(
                    f"[+] Sent {len(request.packet)}-byte "
                    "key-exchange packet"
                )

                response_packet = (
                    v3_camera.receive_common_packet()
                )

                print("\n" + "=" * 72)
                print("RECEIVED COMMON PACKET")
                print("=" * 72)

                print(
                    f"Command: "
                    f"0x{response_packet.command:08x} "
                    f"({response_packet.command})"
                )

                print(
                    f"Version: "
                    f"{response_packet.version}"
                )

                print(
                    "Security mode: "
                    f"{response_packet.security_mode}"
                )

                print(
                    f"Field 6: "
                    f"{response_packet.field_6}"
                )

                print(
                    f"Field 7: "
                    f"{response_packet.field_7}"
                )

                print(
                    f"Reserved: "
                    f"{response_packet.reserved}"
                )

                print(
                    "Payload size: "
                    f"{response_packet.payload_size}"
                )

                if (
                    response_packet.command
                    != COMMON_JSON_COMMAND
                ):
                    print(
                        "[!] Unexpected packet command. "
                        f"Expected "
                        f"0x{COMMON_JSON_COMMAND:08x}, "
                        f"received "
                        f"0x{response_packet.command:08x}."
                    )

                    print(
                        "Raw payload: "
                        f"{response_packet.payload.hex()}"
                    )

                    return 1

                if (
                    response_packet.security_mode
                    != SECURITY_PLAINTEXT
                ):
                    print(
                        "[!] Initial key-exchange "
                        "response was unexpectedly "
                        "encrypted."
                    )

                    print(
                        "Raw payload: "
                        f"{response_packet.payload.hex()}"
                    )

                    return 1

                try:
                    response_json = decode_json_payload(
                        response_packet.payload
                    )

                except (
                    UnicodeDecodeError,
                    json.JSONDecodeError,
                    ValueError,
                ) as error:
                    print(
                        f"[!] Invalid response JSON: "
                        f"{error}"
                    )

                    print(
                        "Raw payload: "
                        f"{response_packet.payload.hex()}"
                    )

                    return 1

                print("\nParsed key-exchange response")
                pprint(response_json)

                response_id = read_integer(
                    response_json,
                    "id",
                )

                response_method = read_integer(
                    response_json,
                    "method_id",
                )

                result_code = read_integer(
                    response_json,
                    "result",
                )

                print("\nResponse values")
                print(f"ID: {response_id}")
                print(f"Method ID: {response_method}")
                print(f"Result: {result_code}")

                if (
                    response_id
                    != key_exchange_data.request_id
                ):
                    print(
                        "[!] Response ID does not "
                        "match the request ID."
                    )

                    return 1

                if (
                    response_method
                    != KEY_EXCHANGE_RESPONSE
                ):
                    print(
                        "[!] Unexpected method ID. "
                        f"Expected "
                        f"{KEY_EXCHANGE_RESPONSE} "
                        f"(0x{KEY_EXCHANGE_RESPONSE:x}), "
                        f"received {response_method}."
                    )

                    return 1

                if (
                    result_code is not None
                    and result_code != 1000
                ):
                    print(
                        "[!] Camera rejected the "
                        "key exchange: "
                        f"result={result_code}"
                    )

                    return 1

                try:
                    result = (
                        parse_key_exchange_response(
                            response_packet.payload,
                            key_exchange_builder.curve_session,
                        )
                    )

                except ValueError as error:
                    print(
                        "[!] Could not parse "
                        "key-exchange response: "
                        f"{error}"
                    )

                    return 1

                print("\n" + "=" * 72)
                print("KEY EXCHANGE SUCCEEDED")
                print("=" * 72)

                print(f"SID: {result.sid}")
                print(f"Expiry: {result.exp}")

                print(
                    "Camera public key: "
                    f"{result.camera_public_key.hex()}"
                )

                print(
                    "Shared secret: "
                    f"{result.shared_secret.hex()}"
                )

                print(
                    f"AES key: "
                    f"{result.aes_key.hex()}"
                )

                print(
                    f"AES IV: "
                    f"{result.aes_iv.hex()}"
                )

                print()
                print(
                    "[+] The V3 socket is still open "
                    "at this point."
                )

                return 0

    except PermissionError as error:
        print(f"[!] Login failed: {error}")
        return 1

    except TimeoutError as error:
        print(f"[!] Timeout: {error}")
        return 1

    except ConnectionError as error:
        print(f"[!] Connection error: {error}")
        return 1

    except OSError as error:
        print(f"[!] Socket error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())