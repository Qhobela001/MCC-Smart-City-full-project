import enum
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class DetectionType(str, enum.Enum):
    noise_pollution = "noise_pollution"
    illegal_dumping = "illegal_dumping"
    skip_overflow = "skip_overflow"
    unauthorized_vending = "unauthorized_vending"
    street_cleaner_non_compliance = "street_cleaner_non_compliance"
    public_urination = "public_urination"
    vehicle_smoke_emission = "vehicle_smoke_emission"
    road_damage = "road_damage"
    pothole = "pothole"
    other = "other"


class DetectionSource(str, enum.Enum):
    camera = "camera"
    uploaded_image = "uploaded_image"
    uploaded_video = "uploaded_video"
    test = "test"


class DetectionReviewStatus(str, enum.Enum):
    unreviewed = "unreviewed"
    confirmed = "confirmed"
    rejected = "rejected"


class AIDetection(Base):
    __tablename__ = "ai_detections"

    id = Column(Integer, primary_key=True, index=True)

    detection_uuid = Column(
        String(36),
        unique=True,
        nullable=False,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )

    detection_type = Column(
        Enum(
            DetectionType,
            name="ai_detection_type",
        ),
        nullable=False,
        index=True,
    )

    class_name = Column(
        String(100),
        nullable=False,
        index=True,
    )

    confidence = Column(
        Float,
        nullable=False,
        index=True,
    )

    detected_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    source_type = Column(
        Enum(
            DetectionSource,
            name="ai_detection_source",
        ),
        default=DetectionSource.camera,
        nullable=False,
        index=True,
    )

    camera_identifier = Column(
        String(100),
        nullable=True,
        index=True,
    )

    stream_identifier = Column(
        String(255),
        nullable=True,
    )

    model_name = Column(
        String(150),
        nullable=False,
        index=True,
    )

    model_version = Column(
        String(100),
        nullable=True,
        index=True,
    )

    # Canonical structured geographic reference.
    gis_location_id = Column(
        Integer,
        ForeignKey(
            "gis_locations.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Immutable-at-event snapshot fields.
    # These remain useful even if a GIS location is renamed later.
    location_name = Column(
        String(255),
        nullable=True,
        index=True,
    )

    latitude = Column(
        Float,
        nullable=True,
    )

    longitude = Column(
        Float,
        nullable=True,
    )

    snapshot_path = Column(
        String(500),
        nullable=True,
    )

    clip_path = Column(
        String(500),
        nullable=True,
    )

    object_count = Column(
        Integer,
        default=1,
        nullable=False,
    )

    attributes = Column(
        JSON,
        default=dict,
        nullable=False,
    )

    incident_id = Column(
        Integer,
        ForeignKey(
            "incidents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    review_status = Column(
        Enum(
            DetectionReviewStatus,
            name="ai_detection_review_status",
        ),
        default=DetectionReviewStatus.unreviewed,
        nullable=False,
        index=True,
    )

    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_test = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    incident = relationship(
        "Incident",
        foreign_keys=[incident_id],
        lazy="joined",
    )

    gis_location = relationship(
        "GISLocation",
        foreign_keys=[gis_location_id],
        lazy="joined",
    )

    reviewed_by = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
        lazy="joined",
    )

    __table_args__ = (
        Index(
            "ix_ai_detections_type_detected_at",
            "detection_type",
            "detected_at",
        ),
        Index(
            "ix_ai_detections_camera_detected_at",
            "camera_identifier",
            "detected_at",
        ),
        Index(
            "ix_ai_detections_gis_detected_at",
            "gis_location_id",
            "detected_at",
        ),
    )
