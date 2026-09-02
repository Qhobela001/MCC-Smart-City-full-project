from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.modules.ai_detections.models import (
    DetectionReviewStatus,
    DetectionSource,
    DetectionType,
)
from app.modules.gis.models import LocationType
from app.modules.incidents.models import IncidentPriority


class AIDetectionGISLocationSummary(BaseModel):
    id: int
    name: str
    code: str
    location_type: LocationType
    latitude: float
    longitude: float
    zone_id: int | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class AIDetectionCreate(BaseModel):
    detection_uuid: str | None = Field(
        default=None,
        max_length=36,
    )

    detection_type: DetectionType
    class_name: str = Field(
        min_length=1,
        max_length=100,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    detected_at: datetime

    source_type: DetectionSource = DetectionSource.camera

    camera_identifier: str | None = Field(
        default=None,
        max_length=100,
    )

    stream_identifier: str | None = Field(
        default=None,
        max_length=255,
    )

    model_name: str = Field(
        min_length=1,
        max_length=150,
    )

    model_version: str | None = Field(
        default=None,
        max_length=100,
    )

    gis_location_id: int | None = Field(
        default=None,
        ge=1,
    )

    location_name: str | None = Field(
        default=None,
        max_length=255,
    )

    latitude: float | None = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: float | None = Field(
        default=None,
        ge=-180,
        le=180,
    )

    snapshot_path: str | None = Field(
        default=None,
        max_length=500,
    )

    clip_path: str | None = Field(
        default=None,
        max_length=500,
    )

    object_count: int = Field(
        default=1,
        ge=0,
    )

    attributes: dict[str, Any] = Field(
        default_factory=dict,
    )

    incident_id: int | None = None

    is_test: bool = False

    @model_validator(mode="after")
    def validate_coordinates(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError(
                "Latitude and longitude must be supplied together."
            )

        return self


class AIDetectionBatchCreate(BaseModel):
    detections: list[AIDetectionCreate] = Field(
        min_length=1,
        max_length=500,
    )


class AIDetectionReview(BaseModel):
    review_status: DetectionReviewStatus
    notes: str = Field(min_length=3, max_length=2000)
    department_id: int | None = Field(default=None, ge=1)
    priority: IncidentPriority | None = None

    @model_validator(mode="after")
    def validate_review_decision(self):
        if self.review_status == DetectionReviewStatus.unreviewed:
            raise ValueError("A completed review must confirm or reject the detection.")
        return self


class ReviewerSummary(BaseModel):
    id: int
    full_name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class AIDetectionRead(BaseModel):
    id: int
    detection_uuid: str

    detection_type: DetectionType
    class_name: str
    confidence: float
    detected_at: datetime

    source_type: DetectionSource

    camera_identifier: str | None
    stream_identifier: str | None

    model_name: str
    model_version: str | None

    gis_location_id: int | None
    gis_location: AIDetectionGISLocationSummary | None = None

    location_name: str | None
    latitude: float | None
    longitude: float | None

    snapshot_path: str | None
    clip_path: str | None

    object_count: int
    attributes: dict[str, Any]

    incident_id: int | None

    review_status: DetectionReviewStatus
    reviewed_by_id: int | None
    reviewed_by: ReviewerSummary | None = None
    reviewed_at: datetime | None

    is_test: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIDetectionListResponse(BaseModel):
    items: list[AIDetectionRead]
    total: int
    page: int
    page_size: int
    pages: int


class AIDetectionBatchResponse(BaseModel):
    created: int
    items: list[AIDetectionRead]
