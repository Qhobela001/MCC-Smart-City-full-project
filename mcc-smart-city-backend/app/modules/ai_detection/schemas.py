from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float
    width: float
    height: float


class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BoundingBox


class RuleAssessmentRead(BaseModel):
    rule: str
    title: str
    status: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    evidence_classes: list[str]
    incident_type: str | None = None


class DetectionResponse(BaseModel):
    filename: str
    image_width: int
    image_height: int
    detections_count: int
    detections: list[DetectionResult]
    rules: list[RuleAssessmentRead]


class VideoClassSummary(BaseModel):
    class_name: str
    max_confidence: float
    detections: int


class VideoDetectionResponse(BaseModel):
    filename: str
    duration_seconds: float
    total_frames: int
    sampled_frames: int
    frame_stride: int
    class_summary: list[VideoClassSummary]
    rules: list[RuleAssessmentRead]


class ModelInfoResponse(BaseModel):
    model_name: str
    number_of_classes: int
    classes: dict[int, str]
