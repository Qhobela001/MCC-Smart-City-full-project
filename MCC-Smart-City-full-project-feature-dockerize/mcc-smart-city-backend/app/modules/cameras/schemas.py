from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.devices.schemas import DeviceSummary, InfrastructureLocationSummary


class CameraStatus(StrEnum):
    planned = "planned"
    configured = "configured"
    online = "online"
    degraded = "degraded"
    offline = "offline"
    maintenance = "maintenance"
    retired = "retired"


class StreamStatus(StrEnum):
    unconfigured = "unconfigured"
    unknown = "unknown"
    online = "online"
    degraded = "degraded"
    offline = "offline"
    disabled = "disabled"


class StreamProtocol(StrEnum):
    rtsp = "rtsp"
    v380 = "v380"


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


def _validate_port(value: int | None) -> int | None:
    if value is None:
        return None
    if value < 1 or value > 65535:
        raise ValueError("Port must be between 1 and 65535.")
    return value


class CameraCreate(BaseModel):
    camera_identifier: str = Field(min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    gis_location_id: int | None = Field(default=None, ge=1)
    assigned_jetson_id: int | None = Field(default=None, ge=1)
    field_nanostation_id: int | None = Field(default=None, ge=1)

    ip_address: str | None = None
    mac_address: str | None = Field(default=None, max_length=32)

    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)

    http_port: int | None = 80
    rtsp_port: int | None = 554
    rtsp_path: str | None = Field(default=None, max_length=500)
    onvif_port: int | None = None

    v380_port: int | None = None
    v380_device_id: int | None = Field(default=None, ge=1)

    stream_protocol: StreamProtocol = StreamProtocol.rtsp

    # credential_reference remains for temporary legacy/env compatibility.
    # New Camera Management writes username/password to the encrypted vault
    # instead; these write-only fields are never part of CameraRead.
    credential_reference: str | None = Field(default=None, max_length=250)
    credential_username: str | None = Field(default=None, max_length=150)
    credential_password: str | None = Field(default=None, max_length=500)

    ai_enabled: bool = True
    ai_profile: dict[str, Any] = Field(default_factory=dict)

    status: CameraStatus = CameraStatus.configured
    stream_status: StreamStatus = StreamStatus.unconfigured

    installed_at: datetime | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        return _validate_ip(value)

    @field_validator("mac_address")
    @classmethod
    def normalize_mac_address(cls, value: str | None) -> str | None:
        return _normalize_mac(value)

    @field_validator("http_port", "rtsp_port", "onvif_port", "v380_port")
    @classmethod
    def validate_ports(cls, value: int | None) -> int | None:
        return _validate_port(value)

    @field_validator("rtsp_path")
    @classmethod
    def reject_embedded_credentials(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None

        lowered = value.lower()
        if lowered.startswith("rtsp://") and "@" in value:
            raise ValueError(
                "Do not store RTSP usernames/passwords in rtsp_path. "
                "Use a path such as /stream1 and keep credentials separate."
            )
        return value


class CameraUpdate(BaseModel):
    camera_identifier: str | None = Field(default=None, min_length=2, max_length=100)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    gis_location_id: int | None = Field(default=None, ge=1)
    assigned_jetson_id: int | None = Field(default=None, ge=1)
    field_nanostation_id: int | None = Field(default=None, ge=1)

    ip_address: str | None = None
    mac_address: str | None = Field(default=None, max_length=32)

    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=150)

    http_port: int | None = None
    rtsp_port: int | None = None
    rtsp_path: str | None = Field(default=None, max_length=500)
    onvif_port: int | None = None

    v380_port: int | None = None
    v380_device_id: int | None = Field(default=None, ge=1)

    stream_protocol: StreamProtocol | None = None
    credential_reference: str | None = Field(default=None, max_length=250)
    credential_username: str | None = Field(default=None, max_length=150)
    credential_password: str | None = Field(default=None, max_length=500)

    ai_enabled: bool | None = None
    ai_profile: dict[str, Any] | None = None

    status: CameraStatus | None = None
    stream_status: StreamStatus | None = None
    is_active: bool | None = None

    installed_at: datetime | None = None

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str | None) -> str | None:
        return _validate_ip(value)

    @field_validator("mac_address")
    @classmethod
    def normalize_mac_address(cls, value: str | None) -> str | None:
        return _normalize_mac(value)

    @field_validator("http_port", "rtsp_port", "onvif_port", "v380_port")
    @classmethod
    def validate_ports(cls, value: int | None) -> int | None:
        return _validate_port(value)

    @field_validator("rtsp_path")
    @classmethod
    def reject_embedded_credentials(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        lowered = value.lower()
        if lowered.startswith("rtsp://") and "@" in value:
            raise ValueError("Do not store RTSP usernames/passwords in rtsp_path.")
        return value


class CameraConnectionTestRequest(BaseModel):
    ip_address: str
    v380_port: int = Field(default=8800, ge=1, le=65535)
    v380_device_id: int = Field(ge=1)
    credential_username: str = Field(min_length=1, max_length=150)
    credential_password: str = Field(min_length=1, max_length=500)

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, value: str) -> str:
        normalized = _validate_ip(value)
        if normalized is None:
            raise ValueError("IP address is required.")
        return normalized


class CameraConnectionTestResponse(BaseModel):
    success: bool
    outcome: str
    login_result: int | None = None
    message: str


class CameraHeartbeatRequest(BaseModel):
    status: CameraStatus = CameraStatus.online
    stream_status: StreamStatus = StreamStatus.unknown


class CameraGatewayHeartbeatResponse(BaseModel):
    camera_id: int
    camera_identifier: str
    status: CameraStatus
    stream_status: StreamStatus
    last_seen_at: datetime | None
    last_stream_check_at: datetime


class CameraCredentialMigrationResponse(BaseModel):
    camera_id: int
    camera_identifier: str
    credential_reference: str
    credential_source: str
    migrated: bool


class CameraRead(BaseModel):
    id: int
    camera_identifier: str
    name: str
    description: str | None

    gis_location_id: int | None
    location: InfrastructureLocationSummary | None

    assigned_jetson_id: int | None
    assigned_jetson: DeviceSummary | None

    field_nanostation_id: int | None
    field_nanostation: DeviceSummary | None

    ip_address: str | None
    mac_address: str | None

    manufacturer: str | None
    model: str | None
    serial_number: str | None

    http_port: int | None
    rtsp_port: int | None
    rtsp_path: str | None
    onvif_port: int | None

    v380_port: int | None
    v380_device_id: int | None

    stream_protocol: StreamProtocol
    credential_reference: str | None
    credential_configured: bool
    credential_source: str | None

    ai_enabled: bool
    ai_profile: dict[str, Any]

    status: CameraStatus
    stream_status: StreamStatus
    is_active: bool

    installed_at: datetime | None
    last_seen_at: datetime | None
    last_stream_check_at: datetime | None

    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CameraListResponse(BaseModel):
    items: list[CameraRead]
    total: int
    page: int
    page_size: int
    pages: int
    can_manage: bool


class CameraSummaryResponse(BaseModel):
    total_cameras: int
    active_cameras: int
    online_cameras: int
    degraded_cameras: int
    offline_cameras: int
    ai_enabled_cameras: int
    mapped_cameras: int
    stream_online_cameras: int
    status_counts: dict[str, int]
    stream_status_counts: dict[str, int]
    can_manage: bool
    generated_at: datetime


class LocationOption(BaseModel):
    id: int
    name: str
    code: str
    latitude: float
    longitude: float
    zone_id: int | None


class DeviceOption(BaseModel):
    id: int
    device_identifier: str
    name: str
    device_type: str
    role: str
    status: str
    gis_location_id: int | None


class CameraOptionsResponse(BaseModel):
    locations: list[LocationOption]
    jetsons: list[DeviceOption]
    nanostations: list[DeviceOption]
    can_manage: bool


class CameraResolveResponse(BaseModel):
    camera_id: int
    camera_identifier: str
    name: str
    gis_location_id: int | None
    location: InfrastructureLocationSummary | None
    assigned_jetson: DeviceSummary | None
    field_nanostation: DeviceSummary | None
    ai_enabled: bool
    status: CameraStatus
