import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.gis import repository
from app.modules.gis.models import GISLocation, GISZone, LocationType, ZoneType
from app.modules.gis.schemas import (
    GISLocationCreate,
    GISLocationListResponse,
    GISLocationRead,
    GISLocationUpdate,
    GISMapDataResponse,
    GISMapDetection,
    GISMapIncident,
    GISSummaryResponse,
    GISZoneCreate,
    GISZoneListResponse,
    GISZoneRead,
    GISZoneSummary,
    GISZoneUpdate,
)
from app.modules.users.models import User


def ensure_superuser(actor: User) -> None:
    if not actor.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "GIS location and zone management is currently restricted "
                "to the MCC Super Administrator."
            ),
        )


def normalize_code(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    return cleaned.strip("-_").upper()


def zone_to_read(zone: GISZone) -> GISZoneRead:
    return GISZoneRead(
        id=zone.id,
        name=zone.name,
        code=zone.code,
        zone_type=zone.zone_type,
        description=zone.description,
        center_latitude=zone.center_latitude,
        center_longitude=zone.center_longitude,
        boundary=zone.boundary or [],
        display_color=zone.display_color,
        is_active=zone.is_active,
        created_by_id=zone.created_by_id,
        location_count=len(zone.locations),
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


def location_to_read(location: GISLocation) -> GISLocationRead:
    zone = (
        GISZoneSummary.model_validate(location.zone)
        if location.zone is not None
        else None
    )
    return GISLocationRead(
        id=location.id,
        name=location.name,
        code=location.code,
        location_type=location.location_type,
        address=location.address,
        description=location.description,
        latitude=location.latitude,
        longitude=location.longitude,
        zone_id=location.zone_id,
        zone=zone,
        is_active=location.is_active,
        created_by_id=location.created_by_id,
        created_at=location.created_at,
        updated_at=location.updated_at,
    )


def get_zone_or_404(db: Session, zone_id: int) -> GISZone:
    zone = repository.get_zone(db, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="GIS zone not found.")
    return zone


def get_location_or_404(db: Session, location_id: int) -> GISLocation:
    location = repository.get_location(db, location_id)
    if location is None:
        raise HTTPException(status_code=404, detail="GIS location not found.")
    return location


def validate_zone_code(
    db: Session,
    code: str,
    current_zone_id: int | None = None,
) -> str:
    normalized = normalize_code(code)
    if not normalized:
        raise HTTPException(status_code=422, detail="Zone code cannot be empty.")
    existing = repository.get_zone_by_code(db, normalized)
    if existing is not None and existing.id != current_zone_id:
        raise HTTPException(
            status_code=409,
            detail="A GIS zone with this code already exists.",
        )
    return normalized


def validate_location_code(
    db: Session,
    code: str,
    current_location_id: int | None = None,
) -> str:
    normalized = normalize_code(code)
    if not normalized:
        raise HTTPException(
            status_code=422,
            detail="Location code cannot be empty.",
        )
    existing = repository.get_location_by_code(db, normalized)
    if existing is not None and existing.id != current_location_id:
        raise HTTPException(
            status_code=409,
            detail="A GIS location with this code already exists.",
        )
    return normalized


def validate_zone_reference(db: Session, zone_id: int | None) -> None:
    if zone_id is not None and repository.get_zone(db, zone_id) is None:
        raise HTTPException(
            status_code=422,
            detail="Selected GIS zone does not exist.",
        )


def list_zones(
    db: Session,
    *,
    active_only: bool,
    search: str | None,
    zone_type: ZoneType | None,
) -> GISZoneListResponse:
    items, total = repository.list_zones(
        db,
        active_only=active_only,
        search=search,
        zone_type=zone_type,
    )
    return GISZoneListResponse(
        items=[zone_to_read(item) for item in items],
        total=total,
    )


def create_zone(
    db: Session,
    payload: GISZoneCreate,
    actor: User,
) -> GISZoneRead:
    ensure_superuser(actor)
    data = payload.model_dump(mode="json")
    data["name"] = payload.name.strip()
    data["code"] = validate_zone_code(db, payload.code)
    data["description"] = (
        payload.description.strip() if payload.description else None
    )
    data["created_by_id"] = actor.id
    return zone_to_read(repository.create_zone(db, data))


def update_zone(
    db: Session,
    zone_id: int,
    payload: GISZoneUpdate,
    actor: User,
) -> GISZoneRead:
    ensure_superuser(actor)
    zone = get_zone_or_404(db, zone_id)
    data = payload.model_dump(exclude_unset=True, mode="json")

    if data.get("name") is not None:
        data["name"] = data["name"].strip()
    if data.get("code") is not None:
        data["code"] = validate_zone_code(db, data["code"], zone.id)
    if "description" in data:
        data["description"] = data["description"].strip() if data["description"] else None

    next_lat = data.get("center_latitude", zone.center_latitude)
    next_lon = data.get("center_longitude", zone.center_longitude)
    if (next_lat is None) != (next_lon is None):
        raise HTTPException(
            status_code=422,
            detail="Zone center latitude and longitude must be supplied together.",
        )

    return zone_to_read(repository.update_zone(db, zone, data))


def delete_zone(
    db: Session,
    zone_id: int,
    actor: User,
) -> None:
    ensure_superuser(actor)
    zone = get_zone_or_404(db, zone_id)
    if zone.locations:
        raise HTTPException(
            status_code=409,
            detail=(
                "This zone still contains GIS locations. "
                "Move or remove those locations first, or deactivate the zone."
            ),
        )
    repository.delete_zone(db, zone)


def list_locations(
    db: Session,
    *,
    active_only: bool,
    search: str | None,
    location_type: LocationType | None,
    zone_id: int | None,
) -> GISLocationListResponse:
    items, total = repository.list_locations(
        db,
        active_only=active_only,
        search=search,
        location_type=location_type,
        zone_id=zone_id,
    )
    return GISLocationListResponse(
        items=[location_to_read(item) for item in items],
        total=total,
    )


def create_location(
    db: Session,
    payload: GISLocationCreate,
    actor: User,
) -> GISLocationRead:
    ensure_superuser(actor)
    validate_zone_reference(db, payload.zone_id)

    data = payload.model_dump(mode="json")
    data["name"] = payload.name.strip()
    data["code"] = validate_location_code(db, payload.code)
    data["address"] = payload.address.strip() if payload.address else None
    data["description"] = (
        payload.description.strip() if payload.description else None
    )
    data["created_by_id"] = actor.id
    return location_to_read(repository.create_location(db, data))


def update_location(
    db: Session,
    location_id: int,
    payload: GISLocationUpdate,
    actor: User,
) -> GISLocationRead:
    ensure_superuser(actor)
    location = get_location_or_404(db, location_id)
    data = payload.model_dump(exclude_unset=True, mode="json")

    if "zone_id" in data:
        validate_zone_reference(db, data["zone_id"])
    if data.get("name") is not None:
        data["name"] = data["name"].strip()
    if data.get("code") is not None:
        data["code"] = validate_location_code(
            db,
            data["code"],
            location.id,
        )
    if "address" in data:
        data["address"] = data["address"].strip() if data["address"] else None
    if "description" in data:
        data["description"] = (
            data["description"].strip() if data["description"] else None
        )

    return location_to_read(repository.update_location(db, location, data))


def delete_location(
    db: Session,
    location_id: int,
    actor: User,
) -> None:
    ensure_superuser(actor)
    repository.delete_location(db, get_location_or_404(db, location_id))


def get_summary(db: Session, actor: User) -> GISSummaryResponse:
    counts = repository.summary_counts(db, actor)
    return GISSummaryResponse(
        **counts,
        can_manage=bool(actor.is_superuser),
        generated_at=datetime.now(timezone.utc),
    )


def get_map_data(
    db: Session,
    actor: User,
) -> GISMapDataResponse:
    incidents = repository.map_incidents(
        db,
        actor,
    )
    detections = repository.map_ai_detections(
        db,
        actor,
    )

    incident_items: list[GISMapIncident] = []

    for incident in incidents:
        if (
            incident.gis_location_id is None
            or incident.location_name is None
            or incident.latitude is None
            or incident.longitude is None
        ):
            continue

        incident_items.append(
            GISMapIncident(
                id=incident.id,
                incident_number=incident.incident_number,
                incident_type=incident.incident_type,
                priority=incident.priority,
                status=incident.status,
                title=incident.title,
                gis_location_id=incident.gis_location_id,
                zone_id=(
                    incident.gis_location.zone_id
                    if incident.gis_location is not None
                    else None
                ),
                location_name=incident.location_name,
                latitude=incident.latitude,
                longitude=incident.longitude,
                reported_at=incident.reported_at,
                is_ai_generated=incident.is_ai_generated,
            )
        )

    detection_items: list[GISMapDetection] = []

    for detection in detections:
        if (
            detection.gis_location_id is None
            or detection.incident_id is None
            or detection.location_name is None
            or detection.latitude is None
            or detection.longitude is None
        ):
            continue

        detection_items.append(
            GISMapDetection(
                id=detection.id,
                detection_type=detection.detection_type,
                class_name=detection.class_name,
                confidence=detection.confidence,
                gis_location_id=detection.gis_location_id,
                zone_id=(
                    detection.gis_location.zone_id
                    if detection.gis_location is not None
                    else None
                ),
                incident_id=detection.incident_id,
                camera_identifier=detection.camera_identifier,
                location_name=detection.location_name,
                latitude=detection.latitude,
                longitude=detection.longitude,
                detected_at=detection.detected_at,
            )
        )

    return GISMapDataResponse(
        incidents=incident_items,
        ai_detections=detection_items,
        generated_at=datetime.now(timezone.utc),
    )
