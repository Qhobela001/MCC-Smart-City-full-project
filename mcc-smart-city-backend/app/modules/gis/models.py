import enum

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
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class ZoneType(str, enum.Enum):
    monitoring = "monitoring"
    vending = "vending"
    no_vending = "no_vending"
    waste_management = "waste_management"
    no_dumping = "no_dumping"
    road_monitoring = "road_monitoring"
    public_space = "public_space"
    municipal_boundary = "municipal_boundary"
    ward = "ward"
    custom = "custom"


class LocationType(str, enum.Enum):
    camera_site = "camera_site"
    intersection = "intersection"
    road_segment = "road_segment"
    market = "market"
    waste_site = "waste_site"
    public_space = "public_space"
    municipal_facility = "municipal_facility"
    other = "other"


class GISZone(Base):
    __tablename__ = "gis_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False, index=True)
    code = Column(String(60), nullable=False, unique=True, index=True)
    zone_type = Column(
        Enum(ZoneType, name="gis_zone_type"),
        nullable=False,
        default=ZoneType.monitoring,
        index=True,
    )
    description = Column(Text, nullable=True)
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)
    boundary = Column(JSON, nullable=False, default=list)
    display_color = Column(String(20), nullable=False, default="#2563EB")
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
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

    locations = relationship(
        "GISLocation",
        back_populates="zone",
        passive_deletes=True,
    )


class GISLocation(Base):
    __tablename__ = "gis_locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(180), nullable=False, index=True)
    code = Column(String(60), nullable=False, unique=True, index=True)
    location_type = Column(
        Enum(LocationType, name="gis_location_type"),
        nullable=False,
        default=LocationType.other,
        index=True,
    )
    address = Column(String(300), nullable=True)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    zone_id = Column(
        Integer,
        ForeignKey("gis_zones.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by_id = Column(
        Integer,
        ForeignKey("users.id"),
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

    zone = relationship("GISZone", back_populates="locations")

    __table_args__ = (
        Index("ix_gis_locations_lat_lon", "latitude", "longitude"),
    )
