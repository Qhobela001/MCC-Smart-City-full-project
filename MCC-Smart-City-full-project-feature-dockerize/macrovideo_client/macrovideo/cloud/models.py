from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CloudRequestConfig:
    """
    Configuration for V380 cloud API requests.
    """

    base_url: str = "https://mapi.av380.net/"
    timeout: float = 20.0
    verify_tls: bool = True

    def __post_init__(self) -> None:
        if not self.base_url:
            raise ValueError(
                "Cloud API base URL cannot be empty."
            )

        if not self.base_url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "Cloud API base URL must begin with "
                "http:// or https://."
            )

        if self.timeout <= 0:
            raise ValueError(
                "Cloud request timeout must be positive."
            )


@dataclass(frozen=True)
class DeviceListRequestOptions:
    """
    Parameters recovered from OkHttpUtil.updateUserDeviceList().
    """

    access_token: str
    from_app: int
    get_sub_server: int
    language: str
    registration_id: str
    version: int = 1008
    device_type: str = "all"
    timestamp: int | None = None

    def __post_init__(self) -> None:
        if not self.access_token:
            raise ValueError(
                "V380 access token cannot be empty."
            )

        if self.from_app < 0:
            raise ValueError(
                "from_app cannot be negative."
            )

        if self.get_sub_server < 0:
            raise ValueError(
                "get_sub_server cannot be negative."
            )

        if not self.language:
            raise ValueError(
                "Request language cannot be empty."
            )

        if self.version <= 0:
            raise ValueError(
                "Application API version must be positive."
            )

        if not self.device_type:
            raise ValueError(
                "Device-list type cannot be empty."
            )


@dataclass(frozen=True)
class CloudDeviceInfo:
    """
    One device returned by POST /device/list.
    """

    device_id: int
    mqsl: str
    protocol_version: int
    rand_key: str
    public_key: str
    from_user_id: int
    account: str
    password: str
    nickname: str
    model: str
    raw_document: dict[str, Any]

    def __post_init__(self) -> None:
        if self.device_id <= 0:
            raise ValueError(
                "Cloud device ID must be positive."
            )

        if self.protocol_version < 0:
            raise ValueError(
                "Cloud device protocol version "
                "cannot be negative."
            )

        if self.from_user_id < 0:
            raise ValueError(
                "Cloud device owner ID cannot be negative."
            )

    @property
    def has_mqtt_information(self) -> bool:
        return bool(
            self.rand_key
            and self.protocol_version > 0
        )

@dataclass(frozen=True)
class DeviceListResult:
    """
    Parsed response from POST /device/list.
    """

    result: int
    error_code: int
    user_id: int
    mqtt_enabled: int
    renew_token: bool
    set_username: bool
    devices: tuple[CloudDeviceInfo, ...]
    shared_devices: tuple[CloudDeviceInfo, ...]
    raw_document: dict[str, Any]

    def __post_init__(self) -> None:
        if self.user_id < 0:
            raise ValueError(
                "Cloud account user ID cannot be negative."
            )

    @property
    def succeeded(self) -> bool:
        return self.result == 0

    def find_device(
        self,
        device_id: int,
    ) -> CloudDeviceInfo | None:
        for device in (
            *self.devices,
            *self.shared_devices,
        ):
            if device.device_id == device_id:
                return device

        return None

    def require_device(
        self,
        device_id: int,
    ) -> CloudDeviceInfo:
        device = self.find_device(device_id)

        if device is None:
            raise LookupError(
                "Device "
                f"{device_id} was not present in the "
                "cloud device-list response."
            )

        return device