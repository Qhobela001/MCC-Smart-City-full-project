from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.ai_detections.models import DetectionType
from app.modules.gis.models import LocationType, ZoneType
from app.modules.incidents.models import (
    IncidentPriority,
    IncidentStatus,
    IncidentType,
)


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)


class GISZoneCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=60)
    zone_type: ZoneType = ZoneType.monitoring
    description: str | None = Field(default=None, max_length=5000)
    center_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    center_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    boundary: list[GeoPoint] = Field(default_factory=list)
    display_color: str = Field(default="#2563EB", min_length=4, max_length=20)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_geometry(self):
        if (self.center_latitude is None) != (self.center_longitude is None):
            raise ValueError(
                "Zone center latitude and longitude must be supplied together."
            )
        if self.boundary and len(self.boundary) < 3:
            raise ValueError(
                "A zone boundary must contain at least three coordinate points."
            )
        return self


class GISZoneUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    zone_type: ZoneType | None = None
    description: str | None = Field(default=None, max_length=5000)
    center_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    center_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    boundary: list[GeoPoint] | None = None
    display_color: str | None = Field(default=None, min_length=4, max_length=20)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_boundary(self):
        if self.boundary is not None and self.boundary and len(self.boundary) < 3:
            raise ValueError(
                "A zone boundary must contain at least three coordinate points."
            )
        return self


class GISZoneSummary(BaseModel):
    id: int
    name: str
    code: str
    zone_type: ZoneType
    display_color: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class GISZoneRead(BaseModel):
    id: int
    name: str
    code: str
    zone_type: ZoneType
    description: str | None
    center_latitude: float | None
    center_longitude: float | None
    boundary: list[GeoPoint]
    display_color: str
    is_active: bool
    created_by_id: int
    location_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GISZoneListResponse(BaseModel):
    items: list[GISZoneRead]
    total: int


class GISLocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=2, max_length=60)
    location_type: LocationType = LocationType.other
    address: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    zone_id: int | None = None
    is_active: bool = True


class GISLocationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    location_type: LocationType | None = None
    address: str | None = Field(default=None, max_length=300)
    description: str | None = Field(default=None, max_length=5000)
    latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    zone_id: int | None = None
    is_active: bool | None = None


class GISLocationRead(BaseModel):
    id: int
    name: str
    code: str
    location_type: LocationType
    address: str | None
    description: str | None
    latitude: float
    longitude: float
    zone_id: int | None
    zone: GISZoneSummary | None = None
    is_active: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GISLocationListResponse(BaseModel):
    items: list[GISLocationRead]
    total: int


class GISSummaryResponse(BaseModel):
    total_zones: int
    active_zones: int
    zones_with_boundaries: int
    total_locations: int
    active_locations: int
    locations_assigned_to_zone: int
    linked_incidents: int
    linked_ai_detections: int
    can_manage: bool
    generated_at: datetime


class GISMapIncident(BaseModel):
    id: int
    incident_number: str
    incident_type: IncidentType
    priority: IncidentPriority
    status: IncidentStatus
    title: str

    gis_location_id: int
    zone_id: int | None

    location_name: str
    latitude: float
    longitude: float

    reported_at: datetime
    is_ai_generated: bool


class GISMapDetection(BaseModel):
    id: int
    detection_type: DetectionType
    class_name: str
    confidence: float

    gis_location_id: int
    zone_id: int | None
    incident_id: int

    camera_identifier: str | None
    location_name: str
    latitude: float
    longitude: float

    detected_at: datetime


class GISMapDataResponse(BaseModel):
    incidents: list[GISMapIncident]
    ai_detections: list[GISMapDetection]
    generated_at: datetime
