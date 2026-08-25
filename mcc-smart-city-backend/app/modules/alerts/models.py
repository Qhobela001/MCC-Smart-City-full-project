import enum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class AlertType(str, enum.Enum):
    incident_created = "incident_created"
    incident_assigned = "incident_assigned"
    incident_status_changed = "incident_status_changed"
    incident_resolved = "incident_resolved"
    evidence_uploaded = "evidence_uploaded"
    system = "system"


class AlertSeverity(str, enum.Enum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    recipient_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recipient_department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    alert_type = Column(
        Enum(AlertType, name="alert_type"),
        nullable=False,
        index=True,
    )
    severity = Column(
        Enum(AlertSeverity, name="alert_severity"),
        default=AlertSeverity.info,
        nullable=False,
        index=True,
    )

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)

    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    is_acknowledged = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    recipient = relationship(
        "User",
        foreign_keys=[recipient_user_id],
        lazy="joined",
    )
    recipient_department = relationship(
        "Department",
        foreign_keys=[recipient_department_id],
        lazy="joined",
    )
    incident = relationship(
        "Incident",
        foreign_keys=[incident_id],
        lazy="joined",
    )
