from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

from macrovideo.protocol.legacy_lan_login import (
    perform_legacy_lan_login,
)
from macrovideo.protocol.legacy_live_stream import (
    LegacyLiveSession,
    probe_legacy_live_stream,
)


CAMERA_HOST = os.getenv(
    "V380_CAMERA_HOST",
    "192.2.42.100",
).strip()
CAMERA_PORT = int(os.getenv("V380_CAMERA_PORT", "8800"))
DEVICE_ID = int(os.getenv("V380_DEVICE_ID", "105848032"))
CAMERA_USERNAME = os.getenv(
    "V380_CAMERA_USERNAME",
    "admin",
).strip()
CAPTURE_SECONDS = float(
    os.getenv("V380_LIVE_CAPTURE_SECONDS", "8")
)
OUTPUT_PATH = Path(
    os.getenv(
        "V380_LIVE_RAW_OUTPUT",
        "v380_live_stream.raw",
    )
)


def resolve_camera_password() -> str:
    value = os.getenv("V380_CAMERA_PASSWORD", "")
    return value or getpass.getpass("Camera password: ")


def main() -> int:
    print("=" * 72)
    print("V380 CORRECTED LEGACY LAN LIVE-STREAM TEST")
    print("=" * 72)

    password = resolve_camera_password()

    print("\nSTEP 1: LEGACY LAN LOGIN")

    try:
        login_exchange = perform_legacy_lan_login(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            device_id=DEVICE_ID,
            username=CAMERA_USERNAME,
            password=password,
        )
    except Exception as error:
        print(
            "[!] LAN login failed: "
            f"{type(error).__name__}: {error}"
        )
        return 1

    login = login_exchange.response

    if not login.succeeded:
        print("[!] Camera rejected the LAN login.")
        return 2

    print("[+] LAN authentication confirmed.")
    print(f"[+] Login handle: {login.handle}")
    print(f"[+] Token session: {login.token_session}")
    print(f"[+] Protocol version: {login.protocol_version}")

    session = LegacyLiveSession(
        device_id=DEVICE_ID,
        login_handle=login.handle,
        token_session=login.token_session,
        protocol_version=login.protocol_version,
    )

    print("\nSTEP 2: SEND CORRECTED DYNAMIC COMMAND 301")

    try:
        result = probe_legacy_live_stream(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            session=session,
            output_path=OUTPUT_PATH,
            capture_seconds=CAPTURE_SECONDS,
        )
    except Exception as error:
        print(
            "[!] Live-stream test failed: "
            f"{type(error).__name__}: {error}"
        )
        return 1

    print("\n" + "=" * 72)
    print("LIVE-STREAM RESULT")
    print("=" * 72)
    print(f"Response command: {result.start_response.command}")
    print(f"Response result: {result.start_response.result}")
    print(f"Raw media bytes: {result.bytes_received}")
    print(f"Saved to: {result.output_path.resolve()}")
    print(
        "First media bytes: "
        f"{result.first_media_bytes.hex()}"
    )

    if result.bytes_received <= 0:
        print("[!] Stream started, but no media bytes arrived.")
        return 3

    print("\n[+] Live media bytes received successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
