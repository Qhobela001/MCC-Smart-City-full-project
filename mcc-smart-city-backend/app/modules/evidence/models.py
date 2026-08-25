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


class EvidenceType(str, enum.Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"
    other = "other"


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(
        Integer,
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    uploaded_by_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    evidence_type = Column(
        Enum(EvidenceType, name="evidence_type"),
        nullable=False,
        index=True,
    )
    original_file_name = Column(String(255), nullable=False)
    stored_file_name = Column(String(255), nullable=False, unique=True)
    relative_path = Column(String(500), nullable=False, unique=True)
    mime_type = Column(String(150), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)

    description = Column(Text, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    is_anonymized = Column(Boolean, default=False, nullable=False)
    is_enforcement_evidence = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    incident = relationship(
        "Incident",
        back_populates="evidence",
    )
    uploaded_by = relationship(
        "User",
        lazy="joined",
    )
