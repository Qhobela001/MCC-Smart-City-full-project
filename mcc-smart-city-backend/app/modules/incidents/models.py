import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class IncidentType(str, enum.Enum):
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


class IncidentPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class IncidentStatus(str, enum.Enum):
    new = "new"
    under_review = "under_review"
    confirmed = "confirmed"
    assigned = "assigned"
    in_progress = "in_progress"
    resolved = "resolved"
    dismissed = "dismissed"


class IncidentSource(str, enum.Enum):
    manual = "manual"
    ai_detection = "ai_detection"
    public_report = "public_report"
    imported = "imported"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(
        String(40),
        unique=True,
        nullable=False,
        index=True,
    )

    incident_type = Column(
        Enum(IncidentType, name="incident_type"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)

    priority = Column(
        Enum(IncidentPriority, name="incident_priority"),
        default=IncidentPriority.medium,
        nullable=False,
        index=True,
    )
    status = Column(
        Enum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.new,
        nullable=False,
        index=True,
    )
    source = Column(
        Enum(IncidentSource, name="incident_source"),
        default=IncidentSource.manual,
        nullable=False,
        index=True,
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
        index=True,
    )
    assigned_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
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

    # Event snapshot fields remain for history/audit.
    location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    is_ai_generated = Column(Boolean, default=False, nullable=False)

    reported_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)

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

    department = relationship(
        "Department",
        lazy="joined",
    )
    assigned_user = relationship(
        "User",
        foreign_keys=[assigned_user_id],
        lazy="joined",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="joined",
    )
    gis_location = relationship(
        "GISLocation",
        foreign_keys=[gis_location_id],
        lazy="joined",
    )
    evidence = relationship(
        "Evidence",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="Evidence.created_at",
    )
    activities = relationship(
        "IncidentActivity",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentActivity.created_at",
    )


class IncidentActivity(Base):
    __tablename__ = "incident_activities"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    action = Column(String(80), nullable=False, index=True)
    previous_status = Column(
        Enum(
            IncidentStatus,
            name="incident_activity_previous_status",
        ),
        nullable=True,
    )
    new_status = Column(
        Enum(
            IncidentStatus,
            name="incident_activity_new_status",
        ),
        nullable=True,
    )
    notes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    incident = relationship(
        "Incident",
        back_populates="activities",
    )
    actor = relationship(
        "User",
        lazy="joined",
    )
