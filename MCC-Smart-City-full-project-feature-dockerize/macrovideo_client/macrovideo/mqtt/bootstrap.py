from __future__ import annotations

from dataclasses import dataclass

from macrovideo.cloud.models import (
    CloudDeviceInfo,
    DeviceListResult,
)

from .models import (
    DeviceMqttInfo,
    MqttConnectionConfig,
)


@dataclass(frozen=True)
class MqttCredentialResult:
    """
    Runtime MQTT connection values returned by the separate
    MQTT credential/bootstrap service.
    """

    broker_url: str
    client_id: str
    username: str
    password: str

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


@dataclass(frozen=True)
class MqttRuntimeContext:
    connection: MqttConnectionConfig
    device: DeviceMqttInfo
    cloud_device: CloudDeviceInfo
    account_uid: int


def build_device_mqtt_info(
    *,
    device_list: DeviceListResult,
    device_id: int,
) -> DeviceMqttInfo:
    if device_id <= 0:
        raise ValueError(
            "Device ID must be positive."
        )

    if device_list.user_id <= 0:
        raise ValueError(
            "The device-list response did not contain "
            "a valid account user ID."
        )

    cloud_device = (
        device_list.require_device(
            device_id
        )
    )

    if not cloud_device.rand_key:
        raise ValueError(
            "The target cloud device has no rk/randKey."
        )

    if cloud_device.protocol_version <= 0:
        raise ValueError(
            "The target cloud device has no valid pver."
        )

    master_id = cloud_device.from_user_id

    if master_id < 0:
        master_id = 0

    return DeviceMqttInfo(
        device_id=cloud_device.device_id,
        account_uid=device_list.user_id,
        rand_key=cloud_device.rand_key,
        protocol_version=(
            cloud_device.protocol_version
        ),
        master_id=master_id,
    )


def build_mqtt_connection_config(
    credentials: MqttCredentialResult,
    *,
    keepalive: int = 60,
) -> MqttConnectionConfig:
    return MqttConnectionConfig(
        broker_url=credentials.broker_url,
        client_id=credentials.client_id,
        username=credentials.username,
        password=credentials.password,
        keepalive=keepalive,
    )


def build_mqtt_runtime_context(
    *,
    device_list: DeviceListResult,
    device_id: int,
    credentials: MqttCredentialResult,
    keepalive: int = 60,
) -> MqttRuntimeContext:
    cloud_device = (
        device_list.require_device(
            device_id
        )
    )

    device = build_device_mqtt_info(
        device_list=device_list,
        device_id=device_id,
    )

    connection = (
        build_mqtt_connection_config(
            credentials,
            keepalive=keepalive,
        )
    )

    return MqttRuntimeContext(
        connection=connection,
        device=device,
        cloud_device=cloud_device,
        account_uid=device_list.user_id,
    )