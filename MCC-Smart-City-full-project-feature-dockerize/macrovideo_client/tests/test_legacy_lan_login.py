from __future__ import annotations

import getpass
import os
import sys

from macrovideo.protocol.legacy_lan_login import (
    LOGIN_RESPONSE_COMMAND,
    perform_legacy_lan_login,
)


CAMERA_HOST = os.getenv(
    "V380_CAMERA_HOST",
    "192.2.42.100",
).strip()

CAMERA_PORT = int(
    os.getenv(
        "V380_CAMERA_PORT",
        "8800",
    )
)

DEVICE_ID = int(
    os.getenv(
        "V380_DEVICE_ID",
        "105848032",
    )
)

CAMERA_USERNAME = os.getenv(
    "V380_CAMERA_USERNAME",
    "admin",
).strip()


def resolve_camera_password() -> str:
    configured = os.getenv(
        "V380_CAMERA_PASSWORD",
        "",
    )

    if configured:
        return configured

    return getpass.getpass(
        "Camera password: "
    )


def main() -> int:
    print("=" * 72)
    print("V380 LEGACY 256-BYTE LAN LOGIN TEST")
    print("=" * 72)

    password = resolve_camera_password()

    if not CAMERA_HOST:
        print("[!] V380_CAMERA_HOST is empty.")
        return 1

    if not CAMERA_USERNAME:
        print("[!] V380_CAMERA_USERNAME is empty.")
        return 1

    if not password:
        print("[!] Camera password is empty.")
        return 1

    print(f"Camera: {CAMERA_HOST}:{CAMERA_PORT}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Camera username: {CAMERA_USERNAME}")
    print("Camera password: <hidden>")

    try:
        exchange = perform_legacy_lan_login(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            device_id=DEVICE_ID,
            username=CAMERA_USERNAME,
            password=password,
            connect_timeout=8.0,
            read_timeout=8.0,
        )
    except Exception as error:
        print(
            "[!] Legacy LAN login failed before a "
            "complete response was parsed: "
            f"{type(error).__name__}: {error}"
        )
        return 1

    response = exchange.response

    print("\n" + "=" * 72)
    print("CAMERA LOGIN RESPONSE")
    print("=" * 72)
    print(
        f"Command: {response.command} "
        f"(expected {LOGIN_RESPONSE_COMMAND})"
    )
    print(f"Login result: {response.login_result}")
    print(f"Result value: {response.result_value}")
    print(f"Normalized error: {response.normalized_error}")
    print(f"Protocol version: {response.protocol_version}")
    print(f"Handle: {response.handle}")
    print(f"Token session: {response.token_session}")
    print(f"Device type: {response.device_type}")
    print(f"Camera type: {response.camera_type}")
    print(f"Channel count: {response.channel_count}")
    print(
        "Response first 64 bytes: "
        f"{response.raw_packet[:64].hex()}"
    )

    if not response.succeeded:
        print("\n[!] Camera returned a login failure.")
        print(
            "[!] If normalized error is 1, verify the "
            "camera password rather than the cloud password."
        )
        return 2

    print("\n[+] Legacy LAN login succeeded.")
    print(
        "[+] We now have the camera handle and token session "
        "needed for subsequent LAN commands."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
