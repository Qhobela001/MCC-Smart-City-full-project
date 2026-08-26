from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LiveCameraRead(BaseModel):
    camera_id: int
    camera_identifier: str
    name: str

    gis_location_id: int | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    status: str
    stream_status: str
    ai_enabled: bool
    is_active: bool

    assigned_jetson_identifier: str | None = None
    assigned_jetson_name: str | None = None
    field_nanostation_identifier: str | None = None

    stream_configured: bool
    gateway_path: str
    gateway_ready: bool | None = None
    viewer_count: int = 0

    last_seen_at: datetime | None = None
    last_stream_check_at: datetime | None = None


class LiveStreamListResponse(BaseModel):
    items: list[LiveCameraRead]
    total: int
    gateway_available: bool
    generated_at: datetime


class GatewayStatusRead(BaseModel):
    available: bool
    generated_at: datetime


class CameraGatewayWorkerHealthRead(BaseModel):
    camera_identifier: str
    status: str
    phase: str
    seconds_since_last_frame: float | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    failure_at: datetime | None = None
    consecutive_failures: int = 0
    retry_seconds: float | None = None


class CameraGatewayHealthRead(BaseModel):
    available: bool
    status: str
    started_at: datetime | None = None
    uptime_seconds: float | None = None
    registry_connected: bool
    registered_cameras: int
    last_registry_sync_at: datetime | None = None
    poll_seconds: float | None = None
    workers_total: int
    workers_alive: int
    workers_online: int
    workers_degraded: int
    workers_offline: int
    failure_code: str | None = None
    failure_message: str | None = None
    failure_at: datetime | None = None
    workers: list[CameraGatewayWorkerHealthRead] = Field(default_factory=list)
    observed_at: datetime | None = None
    generated_at: datetime


class LiveStreamSessionResponse(BaseModel):
    camera: LiveCameraRead
    protocol: str = "webrtc"
    gateway_path: str
    whep_url: str
    token: str
    expires_at: datetime


class SyncFailure(BaseModel):
    camera_identifier: str
    reason: str


class SyncAllResponse(BaseModel):
    synced: list[str] = Field(default_factory=list)
    skipped: list[str] = Field(default_factory=list)
    failed: list[SyncFailure] = Field(default_factory=list)
    gateway_available: bool
    generated_at: datetime


class MediaMTXAuthRequest(BaseModel):
    user: str = ""
    password: str = ""
    token: str = ""
    ip: str = ""
    action: str = ""
    path: str = ""
    protocol: str = ""
    id: str = ""
    query: str = ""
    userAgent: str = ""


class GatewayCameraConfigRead(BaseModel):
    camera_identifier: str
    gateway_path: str
    host: str
    port: int
    device_id: int
    username: str
    password: str
    enabled: bool = True


class GatewayCameraRegistryResponse(BaseModel):
    items: list[GatewayCameraConfigRead] = Field(default_factory=list)
    total: int
    generated_at: datetime
