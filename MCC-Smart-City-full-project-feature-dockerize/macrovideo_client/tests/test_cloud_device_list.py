from __future__ import annotations

import os
import sys
from pprint import pprint

from macrovideo.cloud import (
    CloudRequestConfig,
    DeviceListRequestOptions,
    V380CloudClient,
    build_device_list_request,
    fetch_device_list,
    login_account,
)


DEVICE_ID = 105848032

USERNAME = os.getenv(
    "V380_USERNAME",
    "",
)

PASSWORD = os.getenv(
    "V380_PASSWORD",
    "",
)

FROM_APP = int(
    os.getenv(
        "V380_FROM_APP",
        "0",
    )
)

GET_SUB_SERVER = int(
    os.getenv(
        "V380_GET_SUB_SERVER",
        "10",
    )
)

LANGUAGE = os.getenv(
    "V380_LANGUAGE",
    "en",
)

REGISTRATION_ID = os.getenv(
    "V380_REGISTRATION_ID",
    "",
)

API_BASE_URL = os.getenv(
    "V380_API_BASE_URL",
    "https://mapi.av380.net/",
)

VERIFY_TLS = (
    os.getenv(
        "V380_VERIFY_TLS",
        "true",
    ).strip().lower()
    not in {
        "0",
        "false",
        "no",
    }
)


def mask_secret(
    value: str,
    *,
    visible_start: int = 4,
    visible_end: int = 4,
) -> str:
    if not value:
        return "<empty>"

    if len(value) <= visible_start + visible_end:
        return "*" * len(value)

    hidden_length = (
        len(value)
        - visible_start
        - visible_end
    )

    return (
        value[:visible_start]
        + ("*" * hidden_length)
        + value[-visible_end:]
    )


def main() -> int:
    print("=" * 72)
    print("V380 CLOUD LOGIN + DEVICE-LIST TEST")
    print("=" * 72)

    if not USERNAME:
        print(
            "[!] V380_USERNAME is not configured."
        )
        print(
            '$env:V380_USERNAME = "your-account-email"'
        )
        return 1

    if not PASSWORD:
        print(
            "[!] V380_PASSWORD is not configured."
        )
        print(
            '$env:V380_PASSWORD = "your-account-password"'
        )
        return 1

    try:
        cloud_config = CloudRequestConfig(
            base_url=API_BASE_URL,
            timeout=20.0,
            verify_tls=VERIFY_TLS,
        )
    except ValueError as error:
        print(
            f"[!] Configuration error: {error}"
        )
        return 1

    print("\nCloud configuration")
    print(f"Base URL: {cloud_config.base_url}")
    print(f"Username: {USERNAME}")
    print("Password: <hidden>")
    print(f"TLS verification: {VERIFY_TLS}")

    try:
        with V380CloudClient(
            cloud_config
        ) as client:
            print("\n" + "=" * 72)
            print("STEP 1: ACCOUNT LOGIN")
            print("=" * 72)

            login_result = login_account(
                client,
                username=USERNAME,
                password=PASSWORD,
            )

            print(
                f"Result: {login_result.result}"
            )
            print(
                f"Error code: "
                f"{login_result.error_code}"
            )
            print(
                f"User ID: {login_result.user_id}"
            )
            print(
                "Access token: "
                f"{mask_secret(login_result.access_token)}"
            )

            if not login_result.succeeded:
                print(
                    "\n[!] Account login failed."
                )
                print("\nRaw login response:")
                pprint(
                    login_result.raw_document
                )
                return 1

            print(
                "\n[+] Account login succeeded."
            )

            print("\n" + "=" * 72)
            print("STEP 2: BUILD DEVICE-LIST REQUEST")
            print("=" * 72)

            request_options = (
                DeviceListRequestOptions(
                    access_token=(
                        login_result.access_token
                    ),
                    from_app=FROM_APP,
                    get_sub_server=(
                        GET_SUB_SERVER
                    ),
                    language=LANGUAGE,
                    registration_id=(
                        REGISTRATION_ID
                    ),
                )
            )

            request_document = (
                build_device_list_request(
                    request_options
                )
            )

            printable_request = dict(
                request_document
            )

            printable_request[
                "accesstoken"
            ] = mask_secret(
                request_document[
                    "accesstoken"
                ]
            )

            printable_request[
                "sign"
            ] = mask_secret(
                request_document[
                    "sign"
                ]
            )

            print(
                "\nOutgoing device-list JSON:"
            )
            pprint(printable_request)

            print("\n" + "=" * 72)
            print("STEP 3: FETCH DEVICE LIST")
            print("=" * 72)

            device_list = fetch_device_list(
                client,
                request_options,
            )

    except TimeoutError as error:
        print(f"[!] Timeout: {error}")
        return 1

    except ConnectionError as error:
        print(
            f"[!] Connection error: {error}"
        )
        return 1

    except ValueError as error:
        print(
            "[!] Invalid cloud response: "
            f"{error}"
        )
        return 1

    print(
        f"Result: {device_list.result}"
    )
    print(
        f"Error code: {device_list.error_code}"
    )
    print(
        f"Account user ID: "
        f"{device_list.user_id}"
    )
    print(
        f"MQTT enabled: "
        f"{device_list.mqtt_enabled}"
    )
    print(
        f"Owned devices: "
        f"{len(device_list.devices)}"
    )
    print(
        f"Shared devices: "
        f"{len(device_list.shared_devices)}"
    )

    if not device_list.succeeded:
        print(
            "\n[!] Device-list request failed."
        )
        print("\nRaw response:")
        pprint(
            device_list.raw_document
        )
        return 1

    print("\nDevices returned:")

    all_devices = (
        *device_list.devices,
        *device_list.shared_devices,
    )

    if not all_devices:
        print(
            "[!] The account returned no devices."
        )

    for device in all_devices:
        print("-" * 72)
        print(
            f"Device ID: {device.device_id}"
        )
        print(
            f"Nickname: "
            f"{device.nickname or '<empty>'}"
        )
        print(
            f"Model: "
            f"{device.model or '<empty>'}"
        )
        print(
            f"Protocol version: "
            f"{device.protocol_version}"
        )
        print(
            f"Owner/master ID: "
            f"{device.from_user_id}"
        )
        print(
            f"MQSL: "
            f"{device.mqsl or '<empty>'}"
        )
        print(
            "RK: "
            f"{mask_secret(device.rand_key)}"
        )
        print(
            "Public key: "
            f"{mask_secret(device.public_key)}"
        )
        print(
            "Has MQTT information: "
            f"{device.has_mqtt_information}"
        )

    try:
        selected_device = (
            device_list.require_device(
                DEVICE_ID
            )
        )
    except LookupError as error:
        print(f"\n[!] {error}")
        return 1

    print("\n" + "=" * 72)
    print("TARGET DEVICE FOUND")
    print("=" * 72)

    print(
        f"Device ID: "
        f"{selected_device.device_id}"
    )
    print(
        f"Account UID: "
        f"{device_list.user_id}"
    )
    print(
        f"Owner/master ID: "
        f"{selected_device.from_user_id}"
    )
    print(
        f"Protocol version: "
        f"{selected_device.protocol_version}"
    )
    print(
        f"MQSL: "
        f"{selected_device.mqsl or '<empty>'}"
    )
    print(
        "Rand key present: "
        f"{bool(selected_device.rand_key)}"
    )
    print(
        "Public key present: "
        f"{bool(selected_device.public_key)}"
    )

    if not selected_device.has_mqtt_information:
        print(
            "\n[!] The target device was found, "
            "but its MQTT fields are incomplete."
        )
        print("\nRaw target device:")
        pprint(
            selected_device.raw_document
        )
        return 1

    print(
        "\n[+] Login and device-list "
        "retrieval succeeded."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())