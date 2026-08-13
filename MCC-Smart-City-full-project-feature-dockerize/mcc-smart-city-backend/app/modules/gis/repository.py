from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.modules.ai_detections.models import AIDetection
from app.modules.gis.models import GISLocation, GISZone, LocationType, ZoneType
from app.modules.incidents.models import Incident
from app.modules.incidents.repository import visible_incident_filter
from app.modules.users.models import User


def get_zone(db: Session, zone_id: int) -> GISZone | None:
    return db.query(GISZone).filter(GISZone.id == zone_id).first()


def get_zone_by_code(db: Session, code: str) -> GISZone | None:
    return db.query(GISZone).filter(GISZone.code == code).first()


def list_zones(
    db: Session,
    *,
    active_only: bool = False,
    search: str | None = None,
    zone_type: ZoneType | None = None,
) -> tuple[list[GISZone], int]:
    query = db.query(GISZone)

    if active_only:
        query = query.filter(GISZone.is_active.is_(True))
    if zone_type is not None:
        query = query.filter(GISZone.zone_type == zone_type)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                GISZone.name.ilike(term),
                GISZone.code.ilike(term),
                GISZone.description.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(GISZone.is_active.desc(), GISZone.name.asc()).all()
    return items, total


def create_zone(db: Session, data: dict) -> GISZone:
    zone = GISZone(**data)
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


def update_zone(db: Session, zone: GISZone, data: dict) -> GISZone:
    for key, value in data.items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone: GISZone) -> None:
    db.delete(zone)
    db.commit()


def get_location(db: Session, location_id: int) -> GISLocation | None:
    return db.query(GISLocation).filter(GISLocation.id == location_id).first()


def get_location_by_code(db: Session, code: str) -> GISLocation | None:
    return db.query(GISLocation).filter(GISLocation.code == code).first()


def list_locations(
    db: Session,
    *,
    active_only: bool = False,
    search: str | None = None,
    location_type: LocationType | None = None,
    zone_id: int | None = None,
) -> tuple[list[GISLocation], int]:
    query = db.query(GISLocation)

    if active_only:
        query = query.filter(GISLocation.is_active.is_(True))
    if location_type is not None:
        query = query.filter(GISLocation.location_type == location_type)
    if zone_id is not None:
        query = query.filter(GISLocation.zone_id == zone_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                GISLocation.name.ilike(term),
                GISLocation.code.ilike(term),
                GISLocation.address.ilike(term),
                GISLocation.description.ilike(term),
            )
        )

    total = query.count()
    items = query.order_by(
        GISLocation.is_active.desc(),
        GISLocation.name.asc(),
    ).all()
    return items, total


def create_location(db: Session, data: dict) -> GISLocation:
    location = GISLocation(**data)
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def update_location(
    db: Session,
    location: GISLocation,
    data: dict,
) -> GISLocation:
    for key, value in data.items():
        setattr(location, key, value)
    db.commit()
    db.refresh(location)
    return location


def delete_location(db: Session, location: GISLocation) -> None:
    db.delete(location)
    db.commit()


def summary_counts(db: Session, actor: User) -> dict[str, int]:
    zones = db.query(GISZone).all()
    locations = db.query(GISLocation).all()

    linked_incidents = (
        db.query(Incident)
        .filter(
            visible_incident_filter(actor),
            Incident.gis_location_id.is_not(None),
        )
        .count()
    )

    linked_ai_detections = (
        db.query(AIDetection)
        .join(
            Incident,
            AIDetection.incident_id == Incident.id,
        )
        .filter(
            visible_incident_filter(actor),
            AIDetection.gis_location_id.is_not(None),
            AIDetection.is_test.is_(False),
        )
        .count()
    )

    return {
        "total_zones": len(zones),
        "active_zones": sum(1 for item in zones if item.is_active),
        "zones_with_boundaries": sum(1 for item in zones if item.boundary),
        "total_locations": len(locations),
        "active_locations": sum(1 for item in locations if item.is_active),
        "locations_assigned_to_zone": sum(
            1 for item in locations if item.zone_id is not None
        ),
        "linked_incidents": linked_incidents,
        "linked_ai_detections": linked_ai_detections,
    }


def map_incidents(
    db: Session,
    actor: User,
    *,
    limit: int = 250,
) -> list[Incident]:
    return (
        db.query(Incident)
        .filter(
            visible_incident_filter(actor),
            Incident.gis_location_id.is_not(None),
            Incident.latitude.is_not(None),
            Incident.longitude.is_not(None),
        )
        .order_by(
            Incident.reported_at.desc(),
            Incident.id.desc(),
        )
        .limit(limit)
        .all()
    )


def map_ai_detections(
    db: Session,
    actor: User,
    *,
    limit: int = 500,
) -> list[AIDetection]:
    # Only detections already linked to an incident visible to the actor
    # are surfaced here. This keeps the map aligned with incident access
    # without exposing the full AI-detection feed to every user.
    return (
        db.query(AIDetection)
        .join(
            Incident,
            AIDetection.incident_id == Incident.id,
        )
        .filter(
            visible_incident_filter(actor),
            AIDetection.is_test.is_(False),
            AIDetection.gis_location_id.is_not(None),
            AIDetection.latitude.is_not(None),
            AIDetection.longitude.is_not(None),
        )
        .order_by(
            AIDetection.detected_at.desc(),
            AIDetection.id.desc(),
        )
        .limit(limit)
        .all()
    )
