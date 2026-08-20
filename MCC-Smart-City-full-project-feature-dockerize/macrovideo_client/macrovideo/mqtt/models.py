from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MqttConnectionConfig:
    broker_url: str
    client_id: str
    username: str
    password: str
    keepalive: int = 60

    def __post_init__(self) -> None:
        if not self.broker_url:
            raise ValueError(
                "MQTT broker URL cannot be empty."
            )

        if not self.client_id:
            raise ValueError(
                "MQTT client ID cannot be empty."
            )

        if not self.username:
            raise ValueError(
                "MQTT username cannot be empty."
            )

        if not self.password:
            raise ValueError(
                "MQTT password cannot be empty."
            )

        if self.keepalive <= 0:
            raise ValueError(
                "MQTT keepalive must be greater than zero."
            )


@dataclass(frozen=True)
class DeviceMqttInfo:
    device_id: int
    account_uid: int
    rand_key: str
    protocol_version: int
    master_id: int = 0

    def __post_init__(self) -> None:
        if self.device_id <= 0:
            raise ValueError(
                "Device ID must be greater than zero."
            )

        if self.account_uid <= 0:
            raise ValueError(
                "Account UID must be greater than zero."
            )

        if not self.rand_key:
            raise ValueError(
                "Device MQTT randKey cannot be empty."
            )

        if self.protocol_version < 0:
            raise ValueError(
                "Device protocol version cannot be negative."
            )

        if self.master_id < 0:
            raise ValueError(
                "Master ID cannot be negative."
            )

    @property
    def device_identity(self) -> str:
        return f"CID{self.device_id}"

    @property
    def account_identity(self) -> str:
        return f"UID{self.account_uid}"


@dataclass(frozen=True)
class TurnRelayInfo:
    host: str
    port: int
    handle: int

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError(
                "TURN relay host cannot be empty."
            )

        if not 1 <= self.port <= 65535:
            raise ValueError(
                "TURN relay port must be between "
                "1 and 65535."
            )

        if self.handle < 0:
            raise ValueError(
                "TURN relay handle cannot be negative."
            )


@dataclass(frozen=True)
class WakeupRequest:
    message_id: int
    thread_id: int
    client_uuid: str
    client_public_key: bytes
    response_topic: str
    json_document: dict[str, Any]
    json_text: str
    encrypted_payload: bytes
    publish_topic: str

    def __post_init__(self) -> None:
        if self.message_id <= 0:
            raise ValueError(
                "Wake-up message ID must be positive."
            )

        if self.thread_id <= 0:
            raise ValueError(
                "Wake-up thread ID must be positive."
            )

        if not self.client_uuid:
            raise ValueError(
                "Wake-up UUID cannot be empty."
            )

        if len(self.client_public_key) != 32:
            raise ValueError(
                "Curve25519 public key must contain "
                "exactly 32 bytes."
            )

        if not self.response_topic:
            raise ValueError(
                "Wake-up response topic cannot be empty."
            )

        if not self.publish_topic:
            raise ValueError(
                "Wake-up publish topic cannot be empty."
            )

        if not self.encrypted_payload:
            raise ValueError(
                "Wake-up MQTT payload cannot be empty."
            )


@dataclass(frozen=True)
class WakeupResult:
    call: int
    message_id: int | None
    thread_id: int | None
    result_code: int | None
    result_description: str | None
    raw_document: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        return (
            self.call == 2
            and self.result_code == 1000
        )