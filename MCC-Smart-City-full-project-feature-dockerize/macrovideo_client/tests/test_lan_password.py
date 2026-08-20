from __future__ import annotations

import json
import sys

from macrovideo.config import CameraConfig
from macrovideo.constants import (
    COMMON_JSON_COMMAND,
)
from macrovideo.protocol.lan_password import (
    build_lan_password_request,
)
from macrovideo.protocol.lan_password_response import (
    decrypt_lan_password_payload,
    parse_lan_password_response,
)
from macrovideo.socket_client import CameraSocket


CAMERA_IP = "192.2.42.100"
CAMERA_PORT = 8800

CAMERA_PASSWORD = "Password@9"


def main() -> int:
    print("=" * 72)
    print("V380 LAN-PASSWORD KEY EXCHANGE")
    print("=" * 72)

    config = CameraConfig(
        ip=CAMERA_IP,
        port=CAMERA_PORT,
        timeout=10.0,
    )

    request, curve_session = build_lan_password_request(
        password=CAMERA_PASSWORD,
    )

    print(f"Camera: {CAMERA_IP}:{CAMERA_PORT}")
    print(f"Request ID: {request.request_id}")
    print(f"Magic: {request.magic}")
    print(f"Timestamp: {request.timestamp}")
    print(f"Timezone: {request.timezone}")

    print(
        "Client seed: "
        f"{request.client_seed!r}"
    )

    print(
        "Client public key: "
        f"{request.client_public_key.hex()}"
    )

    print(
        "Masked public key: "
        f"{request.masked_public_key.hex()}"
    )

    print(f"cKM: {request.ckm}")
    print(f"cS: {request.cs}")

    print("\nOutgoing plaintext JSON")
    print(
        request.raw_json.decode("utf-8")
    )

    print("\nOutgoing encrypted packet")
    print(f"Packet size: {len(request.packet)}")
    print(f"Header: {request.packet[:16].hex()}")
    print(
        "Encrypted payload: "
        f"{request.encrypted_payload.hex()}"
    )

    try:
        with CameraSocket(config) as camera:
            print("\n[+] TCP connection established")

            camera.send_all(request.packet)

            print(
                f"[+] Sent {len(request.packet)} bytes"
            )

            response = camera.receive_common_packet()

    except TimeoutError as error:
        print(f"[!] Timeout: {error}")
        return 1

    except ConnectionError as error:
        print(f"[!] Connection error: {error}")
        return 1

    except OSError as error:
        print(f"[!] Socket error: {error}")
        return 1

    print("\nReceived common packet")
    print(
        f"Command: 0x{response.command:08x}"
    )
    print(f"Version: {response.version}")
    print(
        f"Security mode: "
        f"{response.security_mode}"
    )
    print(f"SID/header byte: {response.field_6}")
    print(f"Magic/header byte: {response.field_7}")
    print(f"Payload size: {response.payload_size}")

    if response.command != COMMON_JSON_COMMAND:
        print(
            "[!] Unexpected command: "
            f"0x{response.command:08x}"
        )
        print(
            f"Raw payload: {response.payload.hex()}"
        )
        return 1

    try:
        plaintext = decrypt_lan_password_payload(
            response
        )

        print("\nDecrypted response JSON")
        print(
            plaintext.decode(
                "utf-8",
                errors="replace",
            )
        )

        result = parse_lan_password_response(
            packet=response,
            expected_request_id=request.request_id,
            curve_session=curve_session,
        )

    except PermissionError as error:
        print(f"[!] {error}")
        return 1

    except ValueError as error:
        print(f"[!] Invalid response: {error}")
        print(
            f"Raw response: {response.payload.hex()}"
        )
        return 1

    print("\n" + "=" * 72)
    print("LAN-PASSWORD KEY EXCHANGE SUCCEEDED")
    print("=" * 72)

    print(f"Result code: {result.result_code}")
    print(f"SID: {result.sid}")
    print(f"Permission: {result.perm}")
    print(f"Origin: {result.origin}")

    print(
        "Camera public key: "
        f"{result.camera_public_key.hex()}"
    )

    print(
        "Shared secret: "
        f"{result.shared_secret.hex()}"
    )

    print("\nComplete response object")
    print(
        json.dumps(
            result.raw_json,
            indent=2,
            ensure_ascii=False,
        )
    )

    print()
    print(
        "[+] This SID and 32-byte shared secret are the values "
        "needed for the next live-stream request."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())