from __future__ import annotations

import getpass
import os
import platform
import sys
import time

from macrovideo.cloud import (
    CloudRequestConfig,
    DeviceListRequestOptions,
    MqttClientMetadata,
    V380CloudClient,
    fetch_device_list,
    login_account,
    request_mqtt_credentials,
)
from macrovideo.mqtt.v2_key_exchange import (
    V2KeyExchangeMqttClient,
    build_v2_key_exchange_request,
)
from macrovideo.protocol.mq_socket_key_exchange import (
    open_mq_socket,
    perform_mq_socket_key_exchange_on_socket,
)


DEVICE_ID = int(
    os.getenv(
        "V380_DEVICE_ID",
        "105848032",
    )
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

TCP_CONNECT_TIMEOUT = float(
    os.getenv(
        "V380_TCP_CONNECT_TIMEOUT",
        "8",
    )
)

TCP_READ_TIMEOUT = float(
    os.getenv(
        "V380_TCP_READ_TIMEOUT",
        "18",
    )
)

MQTT_TO_TCP_DELAY = float(
    os.getenv(
        "V380_MQTT_TO_TCP_DELAY",
        "1.0",
    )
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


def mask(
    value: str,
) -> str:
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
    print(
        "V380 PVER=2 MQTT WAKE + "
        "TCP KEY-EXCHANGE TEST"
    )
    print("=" * 72)

    username = resolve_username()
    password = resolve_password()

    if not username or not password:
        print(
            "[!] V380 cloud-account username "
            "or password is empty."
        )
        return 1

    if not CAMERA_HOST:
        print(
            "[!] V380_CAMERA_HOST is empty."
        )
        return 1

    metadata = MqttClientMetadata(
        app_version=os.getenv(
            "V380_APP_VERSION",
            "python-client",
        ),
        system_version=os.getenv(
            "V380_SYSTEM_VERSION",
            platform.platform(),
        ),
        brand=os.getenv(
            "V380_CLIENT_BRAND",
            "Python",
        ),
    )

    try:
        with V380CloudClient(
            CloudRequestConfig(
                base_url=API_BASE_URL,
                timeout=20.0,
                verify_tls=VERIFY_TLS,
            )
        ) as cloud:
            print(
                "\nSTEP 1: CLOUD LOGIN"
            )

            login_result = login_account(
                cloud,
                username=username,
                password=password,
            )

            if not login_result.succeeded:
                print(
                    "[!] Cloud login failed: "
                    f"{login_result.raw_document}"
                )
                return 1

            print(
                "[+] Cloud login succeeded."
            )

            print(
                "\nSTEP 2: DEVICE LIST"
            )

            device_list = fetch_device_list(
                cloud,
                DeviceListRequestOptions(
                    access_token=(
                        login_result.access_token
                    ),
                    from_app=0,
                    get_sub_server=10,
                    language="en",
                    registration_id="",
                ),
            )

            device = (
                device_list.require_device(
                    DEVICE_ID
                )
            )

            print(
                f"[+] Device ID: "
                f"{device.device_id}"
            )
            print(
                "[+] Device protocol version: "
                f"{device.protocol_version}"
            )

            if device.protocol_version >= 3:
                print(
                    "[!] This test implements "
                    "pver < 3, but the device "
                    f"reported pver="
                    f"{device.protocol_version}."
                )
                return 2

            print(
                "\nSTEP 3: MQTT CREDENTIAL "
                "BOOTSTRAP"
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

    except Exception as error:
        print(
            "[!] Cloud/MQTT preparation "
            f"failed: {type(error).__name__}: "
            f"{error}"
        )
        return 1

    print(
        f"[+] Broker: "
        f"{credentials.paho_transport_url}"
    )
    print(
        f"[+] MQTT client ID: "
        f"{mask(credentials.client_id)}"
    )

    print(
        "\nSTEP 4: BUILD LEGACY V2 "
        "MQTT REQUEST"
    )

    try:
        request, curve_session, key_pair = (
            build_v2_key_exchange_request(
                device_id=device.device_id,
                account_uid=(
                    device_list.user_id
                ),
            )
        )

    except Exception as error:
        print(
            "[!] Could not build V2 MQTT "
            f"request: {type(error).__name__}: "
            f"{error}"
        )
        return 1

    print(
        f"Publish topic: "
        f"{request.publish_topic}"
    )
    print(
        f"Client UUID: "
        f"{request.client_uuid}"
    )
    print(
        "Client public key: "
        f"{request.client_public_key.hex()}"
    )
    print(
        f"Client seed: {key_pair.seed!r}"
    )
    print(
        "Plain V2 MQTT JSON:"
    )
    print(
        request.json_text
    )

    mqtt_client = V2KeyExchangeMqttClient(
        broker_url=(
            credentials.paho_transport_url
        ),
        client_id=credentials.client_id,
        username=credentials.username,
        password=credentials.password,
        keepalive=10,
        connect_timeout=15.0,
        response_timeout=0.25,
        tls_verify=VERIFY_TLS,
    )

    print(
        "\nSTEP 5: CONNECT MQTT AND PREPARE "
        "THE CAMERA SOCKET"
    )

    camera_socket = None

    try:
        mqtt_client.connect_and_subscribe(
            account_uid=device_list.user_id,
            device_id=device.device_id,
        )

        print(
            "[>] Starting MQTT publication "
            "without disconnecting MQTT."
        )
        mqtt_client.start_publish(
            request
        )

        print(
            "[>] Opening the camera TCP socket "
            "while the MQTT publication is active."
        )
        camera_socket = open_mq_socket(
            host=CAMERA_HOST,
            port=CAMERA_PORT,
            connect_timeout=(
                TCP_CONNECT_TIMEOUT
            ),
            read_timeout=(
                TCP_READ_TIMEOUT
            ),
        )

        print(
            "[+] Camera TCP socket is open."
        )

        mqtt_client.wait_for_puback()

        print(
            "[+] MQTT PUBACK received while "
            "the TCP socket remained open."
        )

        print(
            "\nSTEP 6: DIRECT CAMERA TCP "
            "KEY EXCHANGE"
        )
        print(
            f"[>] Camera endpoint: "
            f"{CAMERA_HOST}:{CAMERA_PORT}"
        )
        print(
            "[>] Reusing the exact MQTT UUID "
            "and Curve25519 key pair."
        )
        print(
            "[>] MQTT remains connected for "
            "the entire TCP exchange."
        )

        tcp_result = (
            perform_mq_socket_key_exchange_on_socket(
                sock=camera_socket,
                host=CAMERA_HOST,
                port=CAMERA_PORT,
                client_uuid=(
                    request.client_uuid
                ),
                client_public_key=(
                    key_pair.public_key
                ),
                curve_session=(
                    curve_session
                ),
            )
        )

    except Exception as error:
        print(
            "[!] Combined MQTT/TCP exchange "
            f"failed: {type(error).__name__}: "
            f"{error}"
        )
        return 1

    finally:
        if camera_socket is not None:
            camera_socket.close()

        mqtt_client.close()

    exchange = (
        tcp_result.response.key_exchange
    )

    print(
        "\n" + "=" * 72
    )
    print(
        "PVER=2 KEY EXCHANGE SUCCEEDED"
    )
    print(
        "=" * 72
    )
    print(
        "TCP response command: "
        f"0x{tcp_result.response.header.command:08x}"
    )
    print(
        "TCP response payload size: "
        f"{tcp_result.response.payload_size} "
        "bytes"
    )
    print(
        f"Session ID: {exchange.sid}"
    )
    print(
        f"Expiry: {exchange.exp}"
    )
    print(
        "Camera public key: "
        f"{exchange.camera_public_key.hex()}"
    )
    print(
        "Shared secret: "
        f"{exchange.shared_secret.hex()}"
    )
    print(
        f"AES key: {exchange.aes_key.hex()}"
    )
    print(
        f"AES IV: {exchange.aes_iv.hex()}"
    )

    return 0


if __name__ == "__main__":
    sys.exit(
        main()
    )
