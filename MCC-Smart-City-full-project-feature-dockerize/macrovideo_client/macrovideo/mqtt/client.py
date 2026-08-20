from __future__ import annotations

import ssl
import threading
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties

from .models import (
    DeviceMqttInfo,
    MqttConnectionConfig,
    WakeupRequest,
    WakeupResult,
)
from .payload import decrypt_message_payload
from .wakeup import (
    parse_wakeup_response_text,
    validate_wakeup_result,
)


DEFAULT_MQTT_PORT = 1883
DEFAULT_MQTTS_PORT = 8883
DEFAULT_OPERATION_TIMEOUT = 15.0


@dataclass(frozen=True)
class ParsedBrokerUrl:
    host: str
    port: int
    transport: str
    use_tls: bool
    websocket_path: str | None = None


class MqttWakeupClient:
    """
    MQTT v5 wake-up client with explicit diagnostics for:

    - CONNECT acknowledgement;
    - SUBACK;
    - PUBACK;
    - all received MQTT topics;
    - the exact camera wake-up response topic.
    """

    def __init__(
        self,
        connection: MqttConnectionConfig,
        *,
        connect_timeout: float = DEFAULT_OPERATION_TIMEOUT,
        response_timeout: float = DEFAULT_OPERATION_TIMEOUT,
        tls_verify: bool = True,
        diagnostic_topics: Iterable[str] = (),
        log_received_topics: bool = False,
    ) -> None:
        if connect_timeout <= 0:
            raise ValueError(
                "MQTT connect timeout must be positive."
            )

        if response_timeout <= 0:
            raise ValueError(
                "MQTT response timeout must be positive."
            )

        self.connection = connection
        self.connect_timeout = connect_timeout
        self.response_timeout = response_timeout
        self.tls_verify = tls_verify

        self.diagnostic_topics = tuple(
            topic.strip()
            for topic in diagnostic_topics
            if topic.strip()
        )

        self.log_received_topics = (
            log_received_topics
        )

        self._broker = parse_broker_url(
            connection.broker_url
        )

        self._connected = threading.Event()
        self._subscribed = threading.Event()
        self._published = threading.Event()
        self._response_received = threading.Event()
        self._disconnected = threading.Event()

        self._callback_error: Exception | None = None
        self._response_result: WakeupResult | None = None

        self._active_device: DeviceMqttInfo | None = None
        self._active_request: WakeupRequest | None = None

        self._pending_subscription_mids: set[int] = set()
        self._publish_mid: int | None = None

        self._client = self._create_client()

    def _create_client(self) -> mqtt.Client:
        client = mqtt.Client(
            callback_api_version=(
                mqtt.CallbackAPIVersion.VERSION2
            ),
            client_id=self.connection.client_id,
            protocol=mqtt.MQTTv5,
            transport=self._broker.transport,
        )

        client.username_pw_set(
            username=self.connection.username,
            password=self.connection.password,
        )

        if self._broker.transport == "websockets":
            client.ws_set_options(
                path=(
                    self._broker.websocket_path
                    or "/mqtt"
                )
            )

        if self._broker.use_tls:
            self._configure_tls(client)

        client.on_connect = self._on_connect
        client.on_connect_fail = (
            self._on_connect_fail
        )
        client.on_disconnect = self._on_disconnect
        client.on_subscribe = self._on_subscribe
        client.on_publish = self._on_publish
        client.on_message = self._on_message

        return client

    def _configure_tls(
        self,
        client: mqtt.Client,
    ) -> None:
        if self.tls_verify:
            client.tls_set(
                cert_reqs=ssl.CERT_REQUIRED,
                tls_version=(
                    ssl.PROTOCOL_TLS_CLIENT
                ),
            )
            client.tls_insecure_set(False)
        else:
            client.tls_set(
                cert_reqs=ssl.CERT_NONE,
                tls_version=(
                    ssl.PROTOCOL_TLS_CLIENT
                ),
            )
            client.tls_insecure_set(True)

    def wakeup(
        self,
        *,
        device: DeviceMqttInfo,
        request: WakeupRequest,
    ) -> WakeupResult:
        self._prepare_operation(
            device=device,
            request=request,
        )

        try:
            self._client.connect(
                host=self._broker.host,
                port=self._broker.port,
                keepalive=(
                    self.connection.keepalive
                ),
                clean_start=(
                    mqtt.MQTT_CLEAN_START_FIRST_ONLY
                ),
            )
        except OSError as error:
            raise ConnectionError(
                "Could not open MQTT connection to "
                f"{self._broker.host}:"
                f"{self._broker.port}: {error}"
            ) from error

        self._client.loop_start()

        try:
            self._wait_for_event(
                self._connected,
                self.connect_timeout,
                "Timed out while connecting to "
                "MQTT broker.",
            )
            self._raise_callback_error()
            print("[MQTT] CONNECT acknowledged.")

            topics = (
                request.response_topic,
                *self.diagnostic_topics,
            )

            self._subscribe(topics)

            self._wait_for_event(
                self._subscribed,
                self.connect_timeout,
                "Timed out while subscribing to "
                "MQTT topics.",
            )
            self._raise_callback_error()
            print("[MQTT] SUBACK received.")

            self._publish_wakeup(request)

            self._wait_for_event(
                self._published,
                self.connect_timeout,
                "Timed out waiting for MQTT "
                "publish acknowledgement.",
            )
            self._raise_callback_error()
            print("[MQTT] PUBACK received.")

            self._wait_for_event(
                self._response_received,
                self.response_timeout,
                "Timed out waiting for camera "
                "MQTT wake-up response.",
            )
            self._raise_callback_error()

            if self._response_result is None:
                raise RuntimeError(
                    "MQTT response event was set, "
                    "but no result was stored."
                )

            validate_wakeup_result(
                self._response_result,
                request,
            )

            return self._response_result

        finally:
            self._disconnect_cleanly()

    def _prepare_operation(
        self,
        *,
        device: DeviceMqttInfo,
        request: WakeupRequest,
    ) -> None:
        self._connected.clear()
        self._subscribed.clear()
        self._published.clear()
        self._response_received.clear()
        self._disconnected.clear()

        self._callback_error = None
        self._response_result = None

        self._active_device = device
        self._active_request = request

        self._pending_subscription_mids.clear()
        self._publish_mid = None

    def _subscribe(
        self,
        topics: Iterable[str],
    ) -> None:
        unique_topics = tuple(
            dict.fromkeys(topics)
        )

        for topic in unique_topics:
            print(
                f"[MQTT] subscribing: {topic}"
            )

            result, message_id = (
                self._client.subscribe(
                    topic,
                    qos=1,
                )
            )

            if result != mqtt.MQTT_ERR_SUCCESS:
                raise ConnectionError(
                    "MQTT subscribe failed for "
                    f"{topic!r}: "
                    f"{mqtt.error_string(result)}"
                )

            self._pending_subscription_mids.add(
                message_id
            )

    def _publish_wakeup(
        self,
        request: WakeupRequest,
    ) -> None:
        properties = Properties(
            PacketTypes.PUBLISH
        )

        properties.ResponseTopic = (
            request.response_topic
        )

        print(
            "[MQTT] publishing: "
            f"{request.publish_topic}"
        )

        info = self._client.publish(
            topic=request.publish_topic,
            payload=request.encrypted_payload,
            qos=1,
            retain=False,
            properties=properties,
        )

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(
                "MQTT publish failed immediately: "
                f"{mqtt.error_string(info.rc)}"
            )

        self._publish_mid = info.mid

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        del (
            client,
            userdata,
            connect_flags,
            properties,
        )

        if reason_code.is_failure:
            self._callback_error = (
                ConnectionError(
                    "MQTT broker rejected "
                    f"connection: {reason_code}"
                )
            )

        self._connected.set()

    def _on_connect_fail(
        self,
        client: mqtt.Client,
        userdata: Any,
    ) -> None:
        del client, userdata

        self._callback_error = (
            ConnectionError(
                "MQTT connection attempt failed."
            )
        )

        self._connected.set()

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        disconnect_flags: (
            mqtt.DisconnectFlags
        ),
        reason_code: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        del (
            client,
            userdata,
            disconnect_flags,
            properties,
        )

        if (
            reason_code.is_failure
            and self._callback_error is None
        ):
            self._callback_error = (
                ConnectionError(
                    "MQTT connection closed "
                    f"unexpectedly: {reason_code}"
                )
            )

        self._disconnected.set()

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_codes: list[
            mqtt.ReasonCode
        ],
        properties: Properties | None,
    ) -> None:
        del (
            client,
            userdata,
            properties,
        )

        if any(
            code.is_failure
            for code in reason_codes
        ):
            self._callback_error = (
                PermissionError(
                    "MQTT broker rejected "
                    f"subscription MID {mid}: "
                    f"{reason_codes}"
                )
            )

        self._pending_subscription_mids.discard(
            mid
        )

        if not self._pending_subscription_mids:
            self._subscribed.set()

    def _on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code: mqtt.ReasonCode,
        properties: Properties | None,
    ) -> None:
        del (
            client,
            userdata,
            properties,
        )

        if (
            self._publish_mid is not None
            and mid != self._publish_mid
        ):
            return

        if reason_code.is_failure:
            self._callback_error = (
                ConnectionError(
                    "MQTT broker rejected "
                    f"publication: {reason_code}"
                )
            )

        self._published.set()

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata

        print(
            "[MQTT] received "
            f"topic={message.topic!r}, "
            f"payload_size="
            f"{len(message.payload)}"
        )

        device = self._active_device
        request = self._active_request

        if (
            device is None
            or request is None
        ):
            return

        if (
            message.topic
            != request.response_topic
        ):
            return

        try:
            plaintext = decrypt_message_payload(
                payload=bytes(
                    message.payload
                ),
                source=(
                    device.account_identity
                ),
                destination=(
                    device.device_identity
                ),
                rand_key=device.rand_key,
            )

            result = (
                parse_wakeup_response_text(
                    plaintext.decode(
                        "utf-8"
                    ).rstrip("\x00")
                )
            )

            self._response_result = result

        except Exception as error:
            self._callback_error = error

        finally:
            self._response_received.set()

    def _wait_for_event(
        self,
        event: threading.Event,
        timeout: float,
        timeout_message: str,
    ) -> None:
        if not event.wait(timeout):
            raise TimeoutError(
                timeout_message
            )

    def _raise_callback_error(self) -> None:
        if self._callback_error is not None:
            error = self._callback_error
            self._callback_error = None
            raise error

    def _disconnect_cleanly(self) -> None:
        try:
            if self._client.is_connected():
                self._client.disconnect()
                self._disconnected.wait(2.0)
        finally:
            self._client.loop_stop()

    def close(self) -> None:
        self._disconnect_cleanly()


def parse_broker_url(
    url: str,
) -> ParsedBrokerUrl:
    if not url:
        raise ValueError(
            "MQTT broker URL cannot be empty."
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    supported = {
        "mqtt",
        "mqtts",
        "tcp",
        "ssl",
        "ws",
        "wss",
    }

    if scheme not in supported:
        raise ValueError(
            "Unsupported MQTT broker scheme "
            f"{scheme!r}; expected one of "
            f"{sorted(supported)}."
        )

    if not parsed.hostname:
        raise ValueError(
            "MQTT broker URL contains no host."
        )

    use_tls = scheme in {
        "mqtts",
        "ssl",
        "wss",
    }

    transport = (
        "websockets"
        if scheme in {"ws", "wss"}
        else "tcp"
    )

    default_port = (
        DEFAULT_MQTTS_PORT
        if use_tls
        else DEFAULT_MQTT_PORT
    )

    return ParsedBrokerUrl(
        host=parsed.hostname,
        port=(
            parsed.port
            or default_port
        ),
        transport=transport,
        use_tls=use_tls,
        websocket_path=(
            parsed.path
            or None
        ),
    )