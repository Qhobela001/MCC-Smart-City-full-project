from __future__ import annotations

import os
import platform
import sys
from pprint import pprint

from macrovideo.cloud import (
    CloudRequestConfig,
    DeviceListRequestOptions,
    MqttBootstrapError,
    MqttBootstrapUnauthorizedError,
    MqttClientMetadata,
    V380CloudClient,
    build_mqtt_bootstrap_request,
    fetch_device_list,
    login_account,
    request_mqtt_credentials,
)


TARGET_DEVICE_ID = int(
    os.getenv(
        "V380_DEVICE_ID",
        "105848032",
    )
)

USERNAME = os.getenv(
    "V380_USERNAME",
    "",
)

PASSWORD = os.getenv(
    "V380_PASSWORD",
    "",
)

API_BASE_URL = os.getenv(
    "V380_API_BASE_URL",
    "https://mapi.av380.net/",
)

MQTT_LOGIN_SERVER = os.getenv(
    "V380_MQTT_LOGIN_SERVER",
    "gmdev.av380.net:8443",
)

APP_VERSION = os.getenv(
    "V380_APP_VERSION",
    "python-client",
)

SYSTEM_VERSION = os.getenv(
    "V380_SYSTEM_VERSION",
    platform.platform(),
)

CLIENT_BRAND = os.getenv(
    "V380_CLIENT_BRAND",
    "Python",
)

LANGUAGE = os.getenv(
    "V380_LANGUAGE",
    "en",
)

REGISTRATION_ID = os.getenv(
    "V380_REGISTRATION_ID",
    "",
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

    hidden = (
        len(value)
        - visible_start
        - visible_end
    )

    return (
        value[:visible_start]
        + ("*" * hidden)
        + value[-visible_end:]
    )


def main() -> int:
    print("=" * 72)
    print("V380 CLOUD + MQTT CREDENTIAL BOOTSTRAP TEST")
    print("=" * 72)

    if not USERNAME:
        print(
            "[!] V380_USERNAME is not configured."
        )
        return 1

    if not PASSWORD:
        print(
            "[!] V380_PASSWORD is not configured."
        )
        return 1

    metadata = MqttClientMetadata(
        app_version=APP_VERSION,
        system_version=SYSTEM_VERSION,
        brand=CLIENT_BRAND,
    )

    cloud_config = CloudRequestConfig(
        base_url=API_BASE_URL,
        timeout=20.0,
        verify_tls=VERIFY_TLS,
    )

    try:
        with V380CloudClient(
            cloud_config
        ) as client:
            print("\n" + "=" * 72)
            print("STEP 1: CLOUD ACCOUNT LOGIN")
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
                f"Account UID: "
                f"{login_result.user_id}"
            )
            print(
                "Access token: "
                f"{mask_secret(login_result.access_token)}"
            )

            if not login_result.succeeded:
                print(
                    "[!] Cloud account login failed."
                )
                pprint(
                    login_result.raw_document
                )
                return 1

            print(
                "\n[+] Account login succeeded."
            )

            print("\n" + "=" * 72)
            print("STEP 2: DEVICE LIST")
            print("=" * 72)

            options = DeviceListRequestOptions(
                access_token=(
                    login_result.access_token
                ),
                from_app=0,
                get_sub_server=10,
                language=LANGUAGE,
                registration_id=REGISTRATION_ID,
            )

            device_list = fetch_device_list(
                client,
                options,
            )

            print(
                f"Result: {device_list.result}"
            )
            print(
                f"Account UID: "
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

            if not device_list.succeeded:
                print(
                    "[!] Device-list request failed."
                )
                pprint(
                    device_list.raw_document
                )
                return 1

            try:
                target_device = (
                    device_list.require_device(
                        TARGET_DEVICE_ID
                    )
                )
            except LookupError as error:
                print(f"[!] {error}")
                return 1

            print(
                f"Target device: "
                f"{target_device.device_id}"
            )
            print(
                f"Device version: "
                f"{target_device.protocol_version}"
            )
            print(
                "Rand key: "
                f"{mask_secret(target_device.rand_key)}"
            )

            print("\n" + "=" * 72)
            print("STEP 3: BUILD MQTT CREDENTIAL REQUEST")
            print("=" * 72)

            bootstrap_request = (
                build_mqtt_bootstrap_request(
                    account_uid=(
                        device_list.user_id
                    ),
                    access_token=(
                        login_result.access_token
                    ),
                    metadata=metadata,
                    server=MQTT_LOGIN_SERVER,
                )
            )

            printable_document = dict(
                bootstrap_request.document
            )

            printable_document[
                "atoken"
            ] = mask_secret(
                login_result.access_token
            )

            print(
                f"Server: "
                f"{bootstrap_request.server}"
            )
            print(
                f"Timestamp: "
                f"{bootstrap_request.timestamp_ms}"
            )
            print(
                "Signature: "
                f"{mask_secret(bootstrap_request.signature)}"
            )
            print(
                f"URL: https://"
                f"{bootstrap_request.server}"
                "/v1/app/login"
            )

            print("\nOutgoing JSON:")
            pprint(printable_document)

            print("\n" + "=" * 72)
            print("STEP 4: REQUEST MQTT CREDENTIALS")
            print("=" * 72)

            credentials = request_mqtt_credentials(
                account_uid=device_list.user_id,
                access_token=(
                    login_result.access_token
                ),
                metadata=metadata,
                server=MQTT_LOGIN_SERVER,
                timeout=20.0,
                verify_tls=VERIFY_TLS,
            )

    except MqttBootstrapUnauthorizedError as error:
        print(f"[!] Unauthorized: {error}")
        return 1

    except MqttBootstrapError as error:
        print(f"[!] MQTT bootstrap error: {error}")
        return 1

    except TimeoutError as error:
        print(f"[!] Timeout: {error}")
        return 1

    except ConnectionError as error:
        print(f"[!] Connection error: {error}")
        return 1

    except ValueError as error:
        print(f"[!] Invalid data: {error}")
        return 1

    print("\n" + "=" * 72)
    print("MQTT CREDENTIALS RECEIVED")
    print("=" * 72)

    print(f"Response code: {credentials.code}")
    print(
        f"Broker URL: "
        f"{credentials.broker_url}"
    )
    print(
        f"Transport URL: "
        f"{credentials.paho_transport_url}"
    )
    print(
        "Client ID: "
        f"{mask_secret(credentials.client_id)}"
    )
    print(
        "Username: "
        f"{mask_secret(credentials.username)}"
    )
    print(
        "Password: "
        f"{mask_secret(credentials.password)}"
    )
    print(
        f"Expires at: "
        f"{credentials.expires_at}"
    )

    if not credentials.succeeded:
        print(
            "[!] MQTT credentials are incomplete."
        )
        return 1

    print(
        "\n[+] MQTT credential bootstrap succeeded."
    )
    print(
        "[+] The returned values can now replace "
        "all placeholders in the MQTT wake-up test."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())