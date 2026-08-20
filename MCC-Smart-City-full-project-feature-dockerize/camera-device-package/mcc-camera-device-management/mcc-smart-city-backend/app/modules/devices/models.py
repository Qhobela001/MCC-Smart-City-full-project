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


class InfrastructureDevice(Base):
    """
    Registered non-camera infrastructure equipment.

    Cameras intentionally live in their own table because video/RTSP/AI
    configuration is camera-specific. This table covers NanoStations, Jetsons,
    network equipment and future telemetry-capable infrastructure.
    """

    __tablename__ = "infrastructure_devices"

    id = Column(Integer, primary_key=True, index=True)

    device_identifier = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    device_type = Column(String(40), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="other", index=True)

    gis_location_id = Column(
        Integer,
        ForeignKey("gis_locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    parent_device_id = Column(
        Integer,
        ForeignKey("infrastructure_devices.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    ip_address = Column(String(64), nullable=True, index=True)
    mac_address = Column(String(32), nullable=True, unique=True)
    hostname = Column(String(150), nullable=True, index=True)

    manufacturer = Column(String(100), nullable=True)
    model = Column(String(120), nullable=True)
    serial_number = Column(String(150), nullable=True, unique=True)

    configuration = Column(JSON, nullable=False, default=dict)
    health_metrics = Column(JSON, nullable=False, default=dict)

    status = Column(
        String(30),
        nullable=False,
        default="configured",
        index=True,
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    installed_at = Column(DateTime(timezone=True), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

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
    parent_device = relationship(
        "InfrastructureDevice",
        remote_side=[id],
        foreign_keys=[parent_device_id],
        lazy="joined",
    )
    created_by = relationship(
        "User",
        foreign_keys=[created_by_id],
        lazy="joined",
    )

    __table_args__ = (
        Index(
            "ix_infrastructure_devices_type_status",
            "device_type",
            "status",
        ),
        Index(
            "ix_infrastructure_devices_location_type",
            "gis_location_id",
            "device_type",
        ),
    )
