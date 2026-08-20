from __future__ import annotations

import getpass
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
    fetch_device_list,
    login_account,
    request_mqtt_credentials,
)
from macrovideo.mqtt import (
    DeviceMqttInfo,
    MqttConnectionConfig,
    MqttWakeupClient,
    build_device_subscription_topic,
    build_user_subscription_topic,
    build_wakeup_request,
)


DEVICE_ID = int(
    os.getenv(
        "V380_DEVICE_ID",
        "105848032",
    )
)

DEFAULT_USERNAME = (
    "moiloaeric0@gmail.com"
)

API_BASE_URL = os.getenv(
    "V380_API_BASE_URL",
    "https://mapi.av380.net/",
)

MQTT_LOGIN_SERVER = os.getenv(
    "V380_MQTT_LOGIN_SERVER",
    "gmdev.av380.net:8443",
)

LANGUAGE = os.getenv(
    "V380_LANGUAGE",
    "en",
)

REGISTRATION_ID = os.getenv(
    "V380_REGISTRATION_ID",
    "",
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

CONNECT_TIMEOUT = float(
    os.getenv(
        "V380_MQTT_CONNECT_TIMEOUT",
        "15",
    )
)

RESPONSE_TIMEOUT = float(
    os.getenv(
        "V380_MQTT_RESPONSE_TIMEOUT",
        "20",
    )
)

FORCE_UUID_WAKEUP = (
    os.getenv(
        "V380_FORCE_UUID_WAKEUP",
        "false",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
    }
)

DIAGNOSTIC_TOPICS = (
    os.getenv(
        "V380_MQTT_DIAGNOSTIC_TOPICS",
        "false",
    ).strip().lower()
    in {
        "1",
        "true",
        "yes",
    }
)


def resolve_username() -> str:
    return os.getenv(
        "V380_USERNAME",
        DEFAULT_USERNAME,
    ).strip()


def resolve_password() -> str:
    return (
        os.getenv(
            "V380_PASSWORD",
            "",
        )
        or getpass.getpass(
            "V380 account password: "
        )
    )


def mask(value: str) -> str:
    if not value:
        return "<empty>"

    if len(value) <= 8:
        return "*" * len(value)

    return (
        value[:4]
        + "*" * (len(value) - 8)
        + value[-4:]
    )


def main() -> int:
    print("=" * 72)
    print("V380 FULL MQTT WAKE-UP TEST")
    print("=" * 72)

    username = resolve_username()
    password = resolve_password()

    if not username or not password:
        print(
            "[!] Account username or "
            "password is empty."
        )
        return 1

    metadata = MqttClientMetadata(
        app_version=APP_VERSION,
        system_version=SYSTEM_VERSION,
        brand=CLIENT_BRAND,
    )

    try:
        with V380CloudClient(
            CloudRequestConfig(
                base_url=API_BASE_URL,
                timeout=20.0,
                verify_tls=VERIFY_TLS,
            )
        ) as cloud:
            print("\nSTEP 1: CLOUD LOGIN")

            login_result = login_account(
                cloud,
                username=username,
                password=password,
            )

            if not login_result.succeeded:
                pprint(
                    login_result.raw_document
                )
                return 1

            print(
                "[+] Cloud login succeeded."
            )

            print("\nSTEP 2: DEVICE LIST")

            device_list = fetch_device_list(
                cloud,
                DeviceListRequestOptions(
                    access_token=(
                        login_result.access_token
                    ),
                    from_app=0,
                    get_sub_server=10,
                    language=LANGUAGE,
                    registration_id=(
                        REGISTRATION_ID
                    ),
                ),
            )

            cloud_device = (
                device_list.require_device(
                    DEVICE_ID
                )
            )

            print(
                f"[+] Target device: "
                f"{cloud_device.device_id}"
            )

            print(
                f"[+] Protocol version: "
                f"{cloud_device.protocol_version}"
            )

            print(
                "\nSTEP 3: MQTT BOOTSTRAP"
            )

            credentials = (
                request_mqtt_credentials(
                    account_uid=(
                        device_list.user_id
                    ),
                    access_token=(
                        login_result.access_token
                    ),
                    metadata=metadata,
                    server=(
                        MQTT_LOGIN_SERVER
                    ),
                    timeout=45.0,
                    verify_tls=VERIFY_TLS,
                    attempts=3,
                    retry_delay=2.0,
                )
            )

    except (
        MqttBootstrapUnauthorizedError,
        MqttBootstrapError,
        TimeoutError,
        ConnectionError,
        ValueError,
        LookupError,
    ) as error:
        print(
            f"[!] {type(error).__name__}: "
            f"{error}"
        )
        return 1

    master_id = (
        cloud_device.from_user_id
        or device_list.user_id
    )

    print(
        f"[+] Broker: "
        f"{credentials.paho_transport_url}"
    )

    print(
        f"[+] Client ID: "
        f"{mask(credentials.client_id)}"
    )

    connection = MqttConnectionConfig(
        broker_url=(
            credentials.paho_transport_url
        ),
        client_id=credentials.client_id,
        username=credentials.username,
        password=credentials.password,
        keepalive=60,
    )

    device = DeviceMqttInfo(
        device_id=cloud_device.device_id,
        account_uid=device_list.user_id,
        rand_key=cloud_device.rand_key,
        protocol_version=(
            cloud_device.protocol_version
        ),
        master_id=master_id,
    )

    if (
        device.protocol_version < 5
        and not FORCE_UUID_WAKEUP
    ):
        print(
            "[!] Device protocol version is "
            f"{device.protocol_version}."
        )
        print(
            "[!] Current builder is the "
            "unverified UUID/pubKC branch."
        )
        print(
            "[!] No packet sent. Set "
            "V380_FORCE_UUID_WAKEUP=true "
            "only for diagnostics."
        )
        return 2

    try:
        request, curve_session = (
            build_wakeup_request(
                device=device,
            )
        )
    except (
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        print(
            "[!] Could not construct "
            f"wake-up request: {error}"
        )
        return 1

    extra_topics: tuple[str, ...] = ()

    if DIAGNOSTIC_TOPICS:
        extra_topics = (
            "WakeUp/#",
            build_user_subscription_topic(
                device.account_uid
            ),
            build_device_subscription_topic(
                device.device_id
            ),
        )

    print(
        f"\nPublish topic: "
        f"{request.publish_topic}"
    )

    print(
        f"Exact response topic: "
        f"{request.response_topic}"
    )

    if extra_topics:
        print(
            f"Diagnostic topics: "
            f"{extra_topics}"
        )

    mqtt_client = MqttWakeupClient(
        connection,
        connect_timeout=CONNECT_TIMEOUT,
        response_timeout=RESPONSE_TIMEOUT,
        tls_verify=VERIFY_TLS,
        diagnostic_topics=extra_topics,
        log_received_topics=(
            DIAGNOSTIC_TOPICS
        ),
    )

    try:
        result = mqtt_client.wakeup(
            device=device,
            request=request,
        )

    except Exception as error:
        print(
            f"[!] {type(error).__name__}: "
            f"{error}"
        )
        return 1

    print("\nMQTT WAKE-UP SUCCEEDED")
    print(f"Call: {result.call}")
    print(
        f"Message ID: "
        f"{result.message_id}"
    )
    print(
        f"Thread ID: "
        f"{result.thread_id}"
    )
    print(
        f"Result code: "
        f"{result.result_code}"
    )
    print(
        "Description: "
        f"{result.result_description or '<empty>'}"
    )

    pprint(result.raw_document)

    print(
        f"Client UUID: "
        f"{request.client_uuid}"
    )

    print(
        "Client public key: "
        f"{request.client_public_key.hex()}"
    )

    print(
        f"Client seed: "
        f"{curve_session.key_pair.seed!r}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
