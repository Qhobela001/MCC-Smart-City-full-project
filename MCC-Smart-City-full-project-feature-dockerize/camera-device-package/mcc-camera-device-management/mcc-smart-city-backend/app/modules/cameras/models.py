from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Camera(Base):
    """
    Registered MCC field camera.

    Video/network fields live here rather than in the generic infrastructure
    device table because they are specific to camera streaming and AI.
    """

    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)

    camera_identifier = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    gis_location_id = Column(
        Integer,
        ForeignKey("gis_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    assigned_jetson_id = Column(
        Integer,
        ForeignKey("infrastructure_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    field_nanostation_id = Column(
        Integer,
        ForeignKey("infrastructure_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ip_address = Column(String(64), nullable=True, index=True)
    mac_address = Column(String(32), nullable=True, unique=True)

    manufacturer = Column(String(100), nullable=True)
    model = Column(String(120), nullable=True)
    serial_number = Column(String(150), nullable=True, unique=True)

    http_port = Column(Integer, nullable=True, default=80)
    rtsp_port = Column(Integer, nullable=True, default=554)
    rtsp_path = Column(String(500), nullable=True)
    onvif_port = Column(Integer, nullable=True)

    stream_protocol = Column(String(20), nullable=False, default="rtsp")

    # Never store raw passwords in rtsp_path. During hardware integration this
    # can point at a secure secret/config reference.
    credential_reference = Column(String(250), nullable=True)

    ai_enabled = Column(Boolean, nullable=False, default=True, index=True)
    ai_profile = Column(JSON, nullable=False, default=dict)

    status = Column(String(30), nullable=False, default="configured", index=True)
    stream_status = Column(
        String(30),
        nullable=False,
        default="unconfigured",
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    installed_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    last_stream_check_at = Column(DateTime(timezone=True), nullable=True)

    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    location = relationship(
        "GISLocation",
        foreign_keys=[gis_location_id],
        lazy="joined",
    )
    assigned_jetson = relationship(
        "InfrastructureDevice",
        foreign_keys=[assigned_jetson_id],
        lazy="joined",
    )
    field_nanostation = relationship(
        "InfrastructureDevice",
        foreign_keys=[field_nanostation_id],
        lazy="joined",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="joined",
    )

    __table_args__ = (
        Index(
            "ix_cameras_location_status",
            "gis_location_id",
            "status",
        ),
        Index(
            "ix_cameras_jetson_active",
            "assigned_jetson_id",
            "is_active",
        ),
        Index(
            "ix_cameras_nanostation_active",
            "field_nanostation_id",
            "is_active",
        ),
    )
