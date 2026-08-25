from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DeviceType(StrEnum):
    nanostation = "nanostation"
    jetson = "jetson"
    network_switch = "network_switch"
    server = "server"
    solar_controller = "solar_controller"
    battery_monitor = "battery_monitor"
    sensor = "sensor"
    other = "other"


class DeviceRole(StrEnum):
    field_radio = "field_radio"
    hq_radio = "hq_radio"
    edge_ai = "edge_ai"
    hq_ai = "hq_ai"
    network = "network"
    power = "power"
    sensor = "sensor"
    other = "other"


class DeviceStatus(StrEnum):
    planned = "planned"
    configured = "configured"
    online = "online"
    degraded = "degraded"
    offline = "offline"
    maintenance = "maintenance"
    retired = "retired"


def _validate_ip(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        ipaddress.ip_address(value)
    except ValueError as exc:
        raise ValueError("Invalid IP address.") from exc
    return value


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None

    compact = re.sub(r"[^0-9A-Fa-f]", "", value)
    if len(compact) != 12:
        raise ValueError("Invalid MAC address.")

    return ":".join(
        compact[index:index + 2].upper()
        for index in range(0, 12, 2)
    )


class InfrastructureLocationSummary(BaseModel):
    id: int
    name: str
    code: str
    latitude: float
    longitude: float
    zone_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class DeviceSummary(BaseModel):
    id: int
    device_identifier: str
    name: str
    device_type: DeviceType
    role: DeviceRole
    status: DeviceStatus
    gis_location_id: int | None = None


class InfrastructureDeviceCreate(BaseModel):
    device_identifier: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    device_type: DeviceType
    role: DeviceRole = DeviceRole.other

    gis_location_id: int | None = Field(default=None, ge=1)
    parent_device_id: int | None = Field(default=None, ge=1)

    ip_address: str | None = None
    mac_address: str | None = Field(default=None, max_length=32)
    hostname: str | None = Field(default=None, max_length=150)

    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)

    configuration: dict[str, Any] = Field(default_factory=dict)
    status: DeviceStatus = DeviceStatus.configured
    installed_at: datetime | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        return _validate_ip(value)

    @field_validator("mac_address")
    @classmethod
    def normalize_mac_address(cls, value: str | None) -> str | None:
        return _normalize_mac(value)


class InfrastructureDeviceUpdate(BaseModel):
    device_identifier: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    device_type: DeviceType | None = None
    role: DeviceRole | None = None

    gis_location_id: int | None = Field(default=None, ge=1)
    parent_device_id: int | None = Field(default=None, ge=1)

    ip_address: str | None = None
    mac_address: str | None = Field(default=None, max_length=32)
    hostname: str | None = Field(default=None, max_length=150)

    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)

    configuration: dict[str, Any] | None = None
    status: DeviceStatus | None = None
    installed_at: datetime | None = None
    is_active: bool | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        return _validate_ip(value)

    @field_validator("mac_address")
    @classmethod
    def normalize_mac_address(cls, value: str | None) -> str | None:
        return _normalize_mac(value)


class DeviceHeartbeatRequest(BaseModel):
    status: DeviceStatus = DeviceStatus.online
    health_metrics: dict[str, Any] = Field(default_factory=dict)


class InfrastructureDeviceRead(BaseModel):
    id: int
    device_identifier: str
    name: str
    description: str | None

    device_type: DeviceType
    role: DeviceRole

    gis_location_id: int | None
    location: InfrastructureLocationSummary | None
    parent_device_id: int | None
    parent_device: DeviceSummary | None

    ip_address: str | None
    mac_address: str | None
    hostname: str | None

    manufacturer: str | None
    model: str | None
    serial_number: str | None

    configuration: dict[str, Any]
    health_metrics: dict[str, Any]

    status: DeviceStatus
    is_active: bool

    installed_at: datetime | None
    last_seen_at: datetime | None

    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InfrastructureDeviceListResponse(BaseModel):
    items: list[InfrastructureDeviceRead]
    total: int
    page: int
    page_size: int
    pages: int
    can_manage: bool


class InfrastructureDeviceSummaryResponse(BaseModel):
    total_devices: int
    active_devices: int
    online_devices: int
    degraded_devices: int
    offline_devices: int
    type_counts: dict[str, int]
    status_counts: dict[str, int]
    can_manage: bool
    generated_at: datetime
