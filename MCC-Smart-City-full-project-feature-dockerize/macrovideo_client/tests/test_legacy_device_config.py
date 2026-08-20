from __future__ import annotations

import getpass
import json
import os
import sys
from pprint import pprint

from macrovideo.protocol.legacy_device_config import (
    perform_device_config_request,
)
from macrovideo.protocol.legacy_lan_login import (
    perform_legacy_lan_login,
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


def resolve_camera_password() -> str:
    configured = os.getenv("V380_CAMERA_PASSWORD", "")
    return configured or getpass.getpass("Camera password: ")


def main() -> int:
    print("=" * 72)
    print("V380 LEGACY LAN CONFIGURATION DECODER TEST")
    print("=" * 72)

    password = resolve_camera_password()

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

    print(f"[+] LAN login handle: {login.handle}")

    try:
        config = perform_device_config_request(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            device_id=DEVICE_ID,
            login_handle=login.handle,
        )
    except Exception as error:
        print(
            "[!] Device configuration failed: "
            f"{type(error).__name__}: {error}"
        )
        return 1

    print("\n" + "=" * 72)
    print("DECODED DEVICE CONFIGURATION")
    print("=" * 72)

    decoded_summary: dict[str, object] = {}

    for record in config.records:
        print("-" * 72)
        print(
            f"Record {record.index}: "
            f"{record.config_name}"
        )
        pprint(record.decoded_document)
        decoded_summary[
            f"{record.index}_{record.config_name}"
        ] = record.decoded_document

    output_path = os.getenv(
        "V380_CONFIG_JSON_OUTPUT",
        "",
    ).strip()

    if output_path:
        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as output:
            json.dump(
                decoded_summary,
                output,
                indent=2,
                ensure_ascii=False,
            )
        print(
            f"\n[+] Decoded configuration saved to: "
            f"{output_path}"
        )

    if not config.succeeded:
        print("[!] Configuration record set was incomplete.")
        return 3

    print(
        "\n[+] Evidence-backed records decoded successfully."
    )
    print(
        "[+] Types without a confirmed JADX parser remain "
        "preserved as RawConfig instead of being guessed."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
