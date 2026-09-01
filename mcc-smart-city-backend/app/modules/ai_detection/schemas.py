from __future__ import annotations

from typing import Any

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

    # Where the detection came from.
    #
    # primary
    #     = direct YOLO inference from the complete frame
    #
    # vehicle_context / vehicle_detail
    #     = later enhanced pipeline passes
    #
    # For RAW MODEL TESTS this should always be "primary".
    source: str = "primary"

    # The fields below belong to the later tracking/rule pipeline.
    # They stay here because the existing Test Lab already uses them.
    track_id: str | None = None
    parent_detection_index: int | None = None
    tracking_state: str | None = None
    is_predicted: bool = False
    seconds_since_detection: float | None = None

    waste_state: str | None = None
    associated_actor_track_id: str | None = None
    associated_actor_kind: str | None = None
    associated_waste_track_ids: list[str] = Field(default_factory=list)
    dumping_role: str | None = None
    original_class_name: str | None = None


# ===========================================================================
# RAW MODEL TEST
# ===========================================================================
#
# These schemas intentionally contain NO:
#
# - tracking
# - object persistence
# - vehicle recovery
# - secondary inference
# - associations
# - dumping logic
# - smoke rules
# - cleanliness rules
# - incident logic
#
# Their only purpose is to tell us what mcc_detector_v1.pt itself detected.
# ===========================================================================


class RawImageDetectionResponse(BaseModel):
    mode: str = "raw_model"

    filename: str

    image_width: int
    image_height: int

    confidence_threshold: float = Field(
        ge=0.0,
        le=1.0,
    )

    image_size: int

    detections_count: int

    detections: list[DetectionResult]


class RawVideoClassSummary(BaseModel):
    class_name: str

    # Total direct bounding boxes produced for this class.
    detections: int

    # Number of sampled video frames where this class appeared at least once.
    frames_detected: int

    # Percentage of analysed frames containing this class.
    #
    # This is especially important for smoke testing.
    #
    # Example:
    #
    # 300 sampled frames
    # smoke visible to YOLO in 6 frames
    #
    # frame_presence_percent = 2.0
    frame_presence_percent: float = Field(
        ge=0.0,
        le=100.0,
    )

    max_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    mean_confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class RawVideoSampledFrameRead(BaseModel):
    sampled_frame: int

    # Actual frame number in the source video.
    frame_index: int

    time_seconds: float

    image_width: int
    image_height: int

    # DIRECT YOLO detections only.
    detections: list[DetectionResult]


class RawVideoDetectionResponse(BaseModel):
    mode: str = "raw_model"

    filename: str

    duration_seconds: float
    fps: float

    video_width: int
    video_height: int

    total_frames: int
    sampled_frames: int

    requested_frame_stride: int
    effective_frame_stride: int

    analysis_end_seconds: float

    analysis_coverage_percent: float = Field(
        ge=0.0,
        le=100.0,
    )

    confidence_threshold: float = Field(
        ge=0.0,
        le=1.0,
    )

    image_size: int

    total_detections: int

    class_summary: list[RawVideoClassSummary]

    sampled_detections: list[RawVideoSampledFrameRead]


# ===========================================================================
# EXISTING EVENT / RULE PIPELINE
# ===========================================================================


class AssociationRead(BaseModel):
    association_type: str

    left_index: int
    left_class: str
    left_track_id: str | None = None

    right_index: int
    right_class: str
    right_track_id: str | None = None

    relation: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class RuleAssessmentRead(BaseModel):
    rule: str
    title: str
    status: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasons: list[str]
    evidence_classes: list[str]

    incident_type: str | None = None

    related_track_ids: list[str] = Field(
        default_factory=list,
    )

    details: dict[str, Any] = Field(
        default_factory=dict,
    )


class OccurrenceRead(BaseModel):
    occurrence_id: str
    occurrence_type: str
    title: str
    status: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasons: list[str]
    evidence_classes: list[str]

    track_ids: list[str] = Field(
        default_factory=list,
    )

    incident_type: str | None = None

    vehicle_track_id: str | None = None

    person_track_ids: list[str] = Field(
        default_factory=list,
    )

    waste_track_ids: list[str] = Field(
        default_factory=list,
    )

    plate_track_id: str | None = None
    plate_status: str | None = None

    follow_up: str | None = None

    details: dict[str, Any] = Field(
        default_factory=dict,
    )


class StreetCleanlinessRead(BaseModel):
    score: float = Field(
        ge=0.0,
        le=100.0,
    )

    state: str

    loose_waste_count: int
    contained_waste_count: int
    waste_around_skip_count: int
    waste_above_skip_count: int
    total_waste_count: int

    provisional: bool = True

    reasons: list[str]

    before_score: float | None = None
    after_score: float | None = None
    change: float | None = None

    sampled_assessments: int | None = None


class CleanerPerformanceRead(BaseModel):
    status: str
    title: str

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    before_score: float
    after_score: float
    change: float

    reasons: list[str]

    related_track_ids: list[str] = Field(
        default_factory=list,
    )


class DetectionResponse(BaseModel):
    filename: str

    image_width: int
    image_height: int

    detections_count: int

    detections: list[DetectionResult]

    associations: list[AssociationRead]

    rules: list[RuleAssessmentRead]

    occurrences: list[OccurrenceRead]

    street_cleanliness: StreetCleanlinessRead


class VideoClassSummary(BaseModel):
    class_name: str

    max_confidence: float

    detections: int


class VideoTrackSummary(BaseModel):
    track_id: str
    class_name: str

    first_sampled_frame: int
    last_sampled_frame: int

    hits: int

    predicted_frames: int | None = None

    max_confidence: float

    first_seen_seconds: float | None = None
    last_seen_seconds: float | None = None


class AssociationSummary(BaseModel):
    association_type: str
    hits: int


class VideoSampledFrameRead(BaseModel):
    sampled_frame: int

    frame_index: int

    time_seconds: float

    image_width: int
    image_height: int

    detections: list[DetectionResult]


class VideoDetectionResponse(BaseModel):
    filename: str

    duration_seconds: float
    fps: float

    video_width: int
    video_height: int

    total_frames: int
    sampled_frames: int

    frame_stride: int

    requested_frame_stride: int | None = None
    effective_frame_stride: int | None = None

    analysis_end_seconds: float | None = None
    analysis_coverage_percent: float | None = None

    sampled_detections: list[VideoSampledFrameRead]

    predicted_boxes_count: int | None = None

    class_summary: list[VideoClassSummary]

    tracks: list[VideoTrackSummary]

    association_summary: list[AssociationSummary]

    rules: list[RuleAssessmentRead]

    occurrences: list[OccurrenceRead]

    street_cleanliness: StreetCleanlinessRead | None = None

    cleaner_performance: CleanerPerformanceRead | None = None


class ModelInfoResponse(BaseModel):
    model_name: str

    number_of_classes: int

    classes: dict[int, str]