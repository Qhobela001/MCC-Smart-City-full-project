from __future__ import annotations

import base64
import json
import ssl
import threading
import uuid
from dataclasses import dataclass
from typing import Any, Iterable
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from macrovideo.crypto.curve25519 import (
    Curve25519KeyPair,
    Curve25519Session,
)


V2_REQUEST_TOPIC = "svr/request"


@dataclass(frozen=True)
class V2TurnInfo:
    host: str
    port: int | str
    handle: int | str

    def to_document(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "hdl": self.handle,
        }


@dataclass(frozen=True)
class V2KeyExchangeRequest:
    device_id: int
    account_uid: int
    client_uuid: str
    client_public_key: bytes
    publish_topic: str
    json_text: str
    payload: bytes

    @property
    def public_key_base64(self) -> str:
        return base64.b64encode(
            self.client_public_key
        ).decode("ascii")


@dataclass(frozen=True)
class V2ReceivedMessage:
    topic: str
    payload: bytes
    text: str | None
    json_document: Any | None


@dataclass(frozen=True)
class ParsedBrokerUrl:
    host: str
    port: int
    transport: str
    use_tls: bool
    websocket_path: str | None = None


def build_v2_key_exchange_request(
    *,
    device_id: int,
    account_uid: int,
    curve_session: Curve25519Session | None = None,
    client_uuid: str | None = None,
    turn: V2TurnInfo | None = None,
) -> tuple[
    V2KeyExchangeRequest,
    Curve25519Session,
    Curve25519KeyPair,
]:
    """
    Reproduce MqttHelper.publishKeyExchangePver2().

    Android request:

        topic: svr/request
        qos:   1
        body:
        {
          "cmd": 2,
          "auth": {
            "CID": <device id>,
            "uuid": <client uuid>,
            "pubKC": <Base64 client public key>,
            "uid": <account uid>
          }
        }

    The V2 body is plain UTF-8 JSON. It is not wrapped by the
    MessagePayloadTools binary envelope.
    """

    if device_id <= 0:
        raise ValueError(
            "Device ID must be positive."
        )

    if account_uid <= 0:
        raise ValueError(
            "Account UID must be positive."
        )

    session = (
        curve_session
        if curve_session is not None
        else Curve25519Session()
    )

    key_pair = session.generate()

    resolved_uuid = (
        client_uuid.strip()
        if client_uuid is not None
        else str(uuid.uuid4())
    )

    if not resolved_uuid:
        raise ValueError(
            "Client UUID cannot be empty."
        )

    auth: dict[str, Any] = {
        "CID": device_id,
        "uuid": resolved_uuid,
        "pubKC": base64.b64encode(
            key_pair.public_key
        ).decode("ascii"),
        "uid": account_uid,
    }

    document: dict[str, Any] = {
        "cmd": 2,
    }

    if turn is not None:
        document["turn"] = turn.to_document()

    document["auth"] = auth

    json_text = json.dumps(
        document,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    payload = json_text.encode("utf-8")

    return (
        V2KeyExchangeRequest(
            device_id=device_id,
            account_uid=account_uid,
            client_uuid=resolved_uuid,
            client_public_key=key_pair.public_key,
            publish_topic=V2_REQUEST_TOPIC,
            json_text=json_text,
            payload=payload,
        ),
        session,
        key_pair,
    )


class V2KeyExchangeMqttClient:
    """
    Legacy pver=2 MQTT client.

    The staged API mirrors the Android ordering:

        connect MQTT
        subscribe
        start MQTT publication
        open the TCP socket while MQTT remains connected
        wait for PUBACK
        perform the TCP key exchange
        close MQTT only after TCP has completed
    """

    def __init__(
        self,
        *,
        broker_url: str,
        client_id: str,
        username: str,
        password: str,
        keepalive: int = 10,
        connect_timeout: float = 15.0,
        response_timeout: float = 20.0,
        tls_verify: bool = True,
        extra_topics: Iterable[str] = (),
    ) -> None:
        if not client_id:
            raise ValueError(
                "MQTT client ID cannot be empty."
            )

        if not username:
            raise ValueError(
                "MQTT username cannot be empty."
            )

        if not password:
            raise ValueError(
                "MQTT password cannot be empty."
            )

        if keepalive <= 0:
            raise ValueError(
                "MQTT keepalive must be positive."
            )

        self.broker = parse_broker_url(
            broker_url
        )
        self.client_id = client_id
        self.username = username
        self.password = password
        self.keepalive = keepalive
        self.connect_timeout = connect_timeout
        self.response_timeout = response_timeout
        self.tls_verify = tls_verify
        self.extra_topics = tuple(
            topic
            for topic in extra_topics
            if topic
        )

        self._connected = threading.Event()
        self._subscribed = threading.Event()
        self._published = threading.Event()
        self._message_received = threading.Event()
        self._callback_error: Exception | None = None
        self._pending_subscription_mids: set[int] = set()
        self._publish_mid: int | None = None
        self._request_payload: bytes | None = None
        self._loop_started = False
        self.messages: list[V2ReceivedMessage] = []

        self.client = mqtt.Client(
            callback_api_version=(
                mqtt.CallbackAPIVersion.VERSION2
            ),
            client_id=self.client_id,
            protocol=mqtt.MQTTv5,
            transport=self.broker.transport,
        )

        self.client.username_pw_set(
            self.username,
            self.password,
        )

        if self.broker.transport == "websockets":
            self.client.ws_set_options(
                path=(
                    self.broker.websocket_path
                    or "/mqtt"
                )
            )

        if self.broker.use_tls:
            if self.tls_verify:
                self.client.tls_set(
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )
                self.client.tls_insecure_set(False)
            else:
                self.client.tls_set(
                    cert_reqs=ssl.CERT_NONE,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )
                self.client.tls_insecure_set(True)

        self.client.on_connect = self._on_connect
        self.client.on_connect_fail = (
            self._on_connect_fail
        )
        self.client.on_subscribe = self._on_subscribe
        self.client.on_publish = self._on_publish
        self.client.on_message = self._on_message

    def connect_and_subscribe(
        self,
        *,
        account_uid: int,
        device_id: int,
    ) -> None:
        self.messages.clear()
        self._connected.clear()
        self._subscribed.clear()
        self._published.clear()
        self._message_received.clear()
        self._callback_error = None
        self._pending_subscription_mids.clear()
        self._publish_mid = None
        self._request_payload = None

        try:
            self.client.connect(
                self.broker.host,
                self.broker.port,
                keepalive=self.keepalive,
                clean_start=(
                    mqtt.MQTT_CLEAN_START_FIRST_ONLY
                ),
            )
        except OSError as error:
            raise ConnectionError(
                "Could not open MQTT connection to "
                f"{self.broker.host}:"
                f"{self.broker.port}: {error}"
            ) from error

        self.client.loop_start()
        self._loop_started = True

        self._wait(
            self._connected,
            self.connect_timeout,
            "Timed out connecting to MQTT broker.",
        )
        self._raise_callback_error()
        print("[MQTT V2] CONNECT acknowledged.")

        topics = (
            f"UID{account_uid}/#",
            f"UID/UID{account_uid}/#",
            f"CID{device_id}/#",
            f"CID/CID{device_id}/#",
            "svr/#",
            "#",
            *self.extra_topics,
        )

        self._subscribe_topics(topics)

        self._wait(
            self._subscribed,
            self.connect_timeout,
            "Timed out waiting for V2 SUBACK.",
        )
        self._raise_callback_error()
        print("[MQTT V2] SUBACK processing completed.")

    def start_publish(
        self,
        request: V2KeyExchangeRequest,
    ) -> None:
        if not self.client.is_connected():
            raise ConnectionError(
                "MQTT client is not connected."
            )

        self._published.clear()
        self._publish_mid = None
        self._request_payload = request.payload

        info = self.client.publish(
            request.publish_topic,
            request.payload,
            qos=1,
            retain=False,
        )

        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(
                "MQTT V2 publish failed immediately: "
                f"{mqtt.error_string(info.rc)}"
            )

        self._publish_mid = info.mid
        print(
            "[MQTT V2] publication started; "
            f"MID={info.mid}"
        )

    def wait_for_puback(
        self,
        timeout: float | None = None,
    ) -> None:
        resolved_timeout = (
            self.connect_timeout
            if timeout is None
            else timeout
        )

        self._wait(
            self._published,
            resolved_timeout,
            "Timed out waiting for V2 PUBACK.",
        )
        self._raise_callback_error()
        print("[MQTT V2] PUBACK received.")

    def close(self) -> None:
        try:
            if self.client.is_connected():
                self.client.disconnect()
        finally:
            if self._loop_started:
                self.client.loop_stop()
                self._loop_started = False

    def exchange(
        self,
        *,
        request: V2KeyExchangeRequest,
        account_uid: int,
        device_id: int,
    ) -> list[V2ReceivedMessage]:
        """
        Backward-compatible one-shot diagnostic method.
        """
        self.connect_and_subscribe(
            account_uid=account_uid,
            device_id=device_id,
        )

        try:
            self.start_publish(request)
            self.wait_for_puback()

            self._message_received.wait(
                self.response_timeout
            )
            self._raise_callback_error()

            return list(self.messages)
        finally:
            self.close()

    def _subscribe_topics(
        self,
        topics: Iterable[str],
    ) -> None:
        unique = tuple(
            dict.fromkeys(topics)
        )

        accepted = 0

        for topic in unique:
            result, mid = self.client.subscribe(
                topic,
                qos=1,
            )

            if result != mqtt.MQTT_ERR_SUCCESS:
                print(
                    "[MQTT V2] subscribe call rejected "
                    f"locally for {topic!r}: "
                    f"{mqtt.error_string(result)}"
                )
                continue

            accepted += 1
            self._pending_subscription_mids.add(mid)
            print(f"[MQTT V2] subscribing: {topic}")

        if accepted == 0:
            raise ConnectionError(
                "No V2 diagnostic subscription could "
                "be submitted."
            )

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        connect_flags: mqtt.ConnectFlags,
        reason_code: mqtt.ReasonCode,
        properties: Any,
    ) -> None:
        del client, userdata, connect_flags, properties

        if reason_code.is_failure:
            self._callback_error = ConnectionError(
                "MQTT broker rejected connection: "
                f"{reason_code}"
            )

        self._connected.set()

    def _on_connect_fail(
        self,
        client: mqtt.Client,
        userdata: Any,
    ) -> None:
        del client, userdata
        self._callback_error = ConnectionError(
            "MQTT connection attempt failed."
        )
        self._connected.set()

    def _on_subscribe(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_codes: list[mqtt.ReasonCode],
        properties: Any,
    ) -> None:
        del client, userdata, properties

        failed = [
            code
            for code in reason_codes
            if code.is_failure
        ]

        if failed:
            print(
                "[MQTT V2] broker rejected "
                f"subscription MID {mid}: {failed}"
            )

        self._pending_subscription_mids.discard(mid)

        if not self._pending_subscription_mids:
            self._subscribed.set()

    def _on_publish(
        self,
        client: mqtt.Client,
        userdata: Any,
        mid: int,
        reason_code: mqtt.ReasonCode,
        properties: Any,
    ) -> None:
        del client, userdata, properties

        if (
            self._publish_mid is not None
            and mid != self._publish_mid
        ):
            return

        if reason_code.is_failure:
            self._callback_error = ConnectionError(
                "Broker rejected V2 publish: "
                f"{reason_code}"
            )

        self._published.set()

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: Any,
        message: mqtt.MQTTMessage,
    ) -> None:
        del client, userdata

        payload = bytes(message.payload)
        text: str | None = None
        document: Any | None = None

        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            text = None

        if text is not None:
            try:
                document = json.loads(text)
            except json.JSONDecodeError:
                document = None

        received = V2ReceivedMessage(
            topic=message.topic,
            payload=payload,
            text=text,
            json_document=document,
        )
        self.messages.append(received)

        is_echo = (
            message.topic == V2_REQUEST_TOPIC
            and self._request_payload == payload
        )

        print(
            "[MQTT V2] received "
            f"topic={message.topic!r}, "
            f"size={len(payload)}, "
            f"echo={is_echo}"
        )

        if text is not None:
            print(f"[MQTT V2] text: {text}")
        else:
            print(
                "[MQTT V2] binary: "
                f"{payload.hex()}"
            )

        if not is_echo:
            self._message_received.set()

    def _wait(
        self,
        event: threading.Event,
        timeout: float,
        message: str,
    ) -> None:
        if not event.wait(timeout):
            raise TimeoutError(message)

    def _raise_callback_error(self) -> None:
        if self._callback_error is not None:
            error = self._callback_error
            self._callback_error = None
            raise error

def parse_broker_url(
    url: str,
) -> ParsedBrokerUrl:
    if not url:
        raise ValueError(
            "MQTT broker URL cannot be empty."
        )

    parsed = urlparse(url)
    scheme = parsed.scheme.lower()

    if scheme not in {
        "mqtt",
        "mqtts",
        "tcp",
        "ssl",
        "ws",
        "wss",
    }:
        raise ValueError(
            "Unsupported MQTT broker scheme: "
            f"{scheme!r}."
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

    return ParsedBrokerUrl(
        host=parsed.hostname,
        port=(
            parsed.port
            or (8883 if use_tls else 1883)
        ),
        transport=(
            "websockets"
            if scheme in {"ws", "wss"}
            else "tcp"
        ),
        use_tls=use_tls,
        websocket_path=parsed.path or None,
    )
