from datetime import date, datetime

from pydantic import BaseModel

from app.modules.ai_detections.models import DetectionType
from app.modules.ai_detections.schemas import AIDetectionRead


class AnalyticsOverview(BaseModel):
    total_detections: int
    average_confidence: float

    unique_cameras: int
    unique_locations: int

    unreviewed: int
    confirmed: int
    rejected: int

    earliest_detection: datetime | None
    latest_detection: datetime | None


class DetectionTypeAnalytics(BaseModel):
    detection_type: DetectionType
    count: int
    average_confidence: float
    percentage: float


class TrendPoint(BaseModel):
    date: date
    count: int
    average_confidence: float


class LocationAnalytics(BaseModel):
    location_name: str
    count: int
    average_confidence: float


class CameraAnalytics(BaseModel):
    camera_identifier: str
    count: int
    average_confidence: float
    latest_detection: datetime | None


class HourAnalytics(BaseModel):
    hour: int
    count: int
    average_confidence: float


class ModelPerformanceAnalytics(BaseModel):
    model_name: str
    model_version: str | None

    detections: int

    average_confidence: float
    minimum_confidence: float
    maximum_confidence: float

    unreviewed: int
    confirmed: int
    rejected: int


class RecentDetectionsResponse(BaseModel):
    items: list[AIDetectionRead]