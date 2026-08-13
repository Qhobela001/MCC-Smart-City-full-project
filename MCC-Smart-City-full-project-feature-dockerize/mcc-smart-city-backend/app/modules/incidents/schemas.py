from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.gis.models import LocationType
from app.modules.incidents.models import (
    IncidentPriority,
    IncidentSource,
    IncidentStatus,
    IncidentType,
)


class DepartmentSummary(BaseModel):
    id: int
    name: str
    code: str

    model_config = ConfigDict(from_attributes=True)


class UserSummary(BaseModel):
    id: int
    full_name: str
    email: str
    employee_number: str | None = None

    model_config = ConfigDict(from_attributes=True)


class IncidentGISLocationSummary(BaseModel):
    id: int
    name: str
    code: str
    location_type: LocationType
    latitude: float
    longitude: float
    zone_id: int | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class IncidentCreate(BaseModel):
    incident_type: IncidentType
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=3, max_length=5000)
    priority: IncidentPriority = IncidentPriority.medium
    source: IncidentSource = IncidentSource.manual

    department_id: int | None = None
    assigned_user_id: int | None = None

    gis_location_id: int | None = Field(
        default=None,
        ge=1,
    )

    location_name: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    is_ai_generated: bool = False

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be supplied together."
            )
        return self


class IncidentUpdate(BaseModel):
    incident_type: IncidentType | None = None
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(
        default=None,
        min_length=3,
        max_length=5000,
    )
    priority: IncidentPriority | None = None
    department_id: int | None = None

    gis_location_id: int | None = Field(
        default=None,
        ge=1,
    )

    location_name: str | None = Field(default=None, max_length=255)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            if self.latitude is not None or self.longitude is not None:
                raise ValueError(
                    "Latitude and longitude must be supplied together."
                )
        return self


class IncidentAssignment(BaseModel):
    assigned_user_id: int
    department_id: int | None = None
    notes: str | None = Field(default=None, max_length=2000)


class IncidentStatusChange(BaseModel):
    status: IncidentStatus
    notes: str | None = Field(default=None, max_length=3000)
    resolution_notes: str | None = Field(
        default=None,
        max_length=5000,
    )


class IncidentActivityRead(BaseModel):
    id: int
    incident_id: int
    actor_user_id: int
    action: str
    previous_status: IncidentStatus | None
    new_status: IncidentStatus | None
    notes: str | None
    actor: UserSummary
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IncidentRead(BaseModel):
    id: int
    incident_number: str
    incident_type: IncidentType
    title: str
    description: str
    priority: IncidentPriority
    status: IncidentStatus
    source: IncidentSource

    department_id: int | None
    assigned_user_id: int | None
    created_by_id: int

    department: DepartmentSummary | None = None
    assigned_user: UserSummary | None = None
    created_by: UserSummary

    gis_location_id: int | None
    gis_location: IncidentGISLocationSummary | None = None

    location_name: str | None
    latitude: float | None
    longitude: float | None
    is_ai_generated: bool

    reported_at: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    resolution_notes: str | None

    created_at: datetime
    updated_at: datetime

    evidence_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class IncidentListResponse(BaseModel):
    items: list[IncidentRead]
    total: int
    page: int
    page_size: int
    pages: int
