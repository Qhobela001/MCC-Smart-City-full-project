from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.devices import repository
from app.modules.devices.models import InfrastructureDevice
from app.modules.devices.schemas import (
    DeviceHeartbeatRequest,
    DeviceSummary,
    InfrastructureDeviceCreate,
    InfrastructureDeviceListResponse,
    InfrastructureDeviceRead,
    InfrastructureDeviceSummaryResponse,
    InfrastructureDeviceUpdate,
    InfrastructureLocationSummary,
)
from app.modules.gis.models import GISLocation
from app.modules.users.models import User


def normalize_identifier(value: str) -> str:
    normalized = re.sub(r"[^A-Z0-9]+", "-", value.strip().upper()).strip("-")
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Device identifier cannot be empty.",
        )
    return normalized


def ensure_manager(actor: User) -> None:
    if actor.is_superuser:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the Super Administrator can modify infrastructure devices.",
    )


def _get_active_location(db: Session, location_id: int | None) -> GISLocation | None:
    if location_id is None:
        return None
    location = db.scalar(
        select(GISLocation).where(
            GISLocation.id == location_id,
            GISLocation.is_active.is_(True),
        )
    )
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected GIS location does not exist or is inactive.",
        )
    return location


def _get_parent(
    db: Session,
    parent_device_id: int | None,
    *,
    current_device_id: int | None = None,
) -> InfrastructureDevice | None:
    if parent_device_id is None:
        return None
    if current_device_id is not None and parent_device_id == current_device_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A device cannot be its own parent.",
        )
    parent = repository.get_device(db, parent_device_id)
    if parent is None or not parent.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Selected parent device does not exist or is inactive.",
        )
    return parent


def _duplicate_conflict(
    db: Session,
    *,
    device_identifier: str | None = None,
    mac_address: str | None = None,
    serial_number: str | None = None,
    exclude_id: int | None = None,
) -> None:
    candidates: list[tuple[InfrastructureDevice | None, str]] = []
    if device_identifier:
        candidates.append((repository.get_by_identifier(db, device_identifier), "device identifier"))
    if mac_address:
        candidates.append((repository.get_by_mac(db, mac_address), "MAC address"))
    if serial_number:
        candidates.append((repository.get_by_serial(db, serial_number), "serial number"))

    for existing, label in candidates:
        if existing is None:
            continue
        if exclude_id is not None and existing.id == exclude_id:
            continue
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Another infrastructure device already uses this {label}.",
        )


def create_device(
    db: Session,
    payload: InfrastructureDeviceCreate,
    *,
    actor: User,
) -> InfrastructureDevice:
    ensure_manager(actor)
    identifier = normalize_identifier(payload.device_identifier)
    _get_active_location(db, payload.gis_location_id)
    _get_parent(db, payload.parent_device_id)

    _duplicate_conflict(
        db,
        device_identifier=identifier,
        mac_address=payload.mac_address,
        serial_number=payload.serial_number,
    )

    values = payload.model_dump()
    values["device_identifier"] = identifier
    values["device_type"] = payload.device_type.value
    values["role"] = payload.role.value
    values["status"] = payload.status.value
    values["created_by_id"] = actor.id

    try:
        device = repository.create_device(db, values)
        db.commit()
        db.refresh(device)
        return device
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Infrastructure device could not be created because a unique value already exists.",
        ) from exc


def get_device_or_404(db: Session, device_id: int) -> InfrastructureDevice:
    device = repository.get_device(db, device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Infrastructure device not found.",
        )
    return device


def update_device(
    db: Session,
    device: InfrastructureDevice,
    payload: InfrastructureDeviceUpdate,
    *,
    actor: User,
) -> InfrastructureDevice:
    ensure_manager(actor)
    values = payload.model_dump(exclude_unset=True)

    if values.get("device_identifier") is not None:
        values["device_identifier"] = normalize_identifier(values["device_identifier"])
    if values.get("device_type") is not None:
        values["device_type"] = values["device_type"].value
    if values.get("role") is not None:
        values["role"] = values["role"].value
    if values.get("status") is not None:
        values["status"] = values["status"].value
    if "gis_location_id" in values:
        _get_active_location(db, values["gis_location_id"])
    if "parent_device_id" in values:
        _get_parent(db, values["parent_device_id"], current_device_id=device.id)

    _duplicate_conflict(
        db,
        device_identifier=values.get("device_identifier", device.device_identifier),
        mac_address=values.get("mac_address", device.mac_address),
        serial_number=values.get("serial_number", device.serial_number),
        exclude_id=device.id,
    )

    if "device_type" in values and values["device_type"] != device.device_type:
        from app.modules.cameras.models import Camera

        camera_reference_count = int(
            db.scalar(
                select(func.count(Camera.id)).where(
                    Camera.is_active.is_(True),
                    (
                        (Camera.assigned_jetson_id == device.id)
                        | (Camera.field_nanostation_id == device.id)
                    ),
                )
            )
            or 0
        )
        if camera_reference_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device type cannot be changed while active cameras reference this device.",
            )

    if values.get("status") == "retired":
        values["is_active"] = False

    try:
        repository.update_device(db, device, values)
        db.commit()
        db.refresh(device)
        return device
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Infrastructure device could not be updated because a unique value already exists.",
        ) from exc


def retire_device(
    db: Session,
    device: InfrastructureDevice,
    *,
    actor: User,
) -> InfrastructureDevice:
    ensure_manager(actor)
    from app.modules.cameras.models import Camera

    active_camera_references = int(
        db.scalar(
            select(func.count(Camera.id)).where(
                Camera.is_active.is_(True),
                (
                    (Camera.assigned_jetson_id == device.id)
                    | (Camera.field_nanostation_id == device.id)
                ),
            )
        )
        or 0
    )
    active_children = repository.list_active_children(db, device.id)

    if active_camera_references or active_children:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Device cannot be retired while it is referenced by an active "
                "camera or child infrastructure device."
            ),
        )

    repository.update_device(
        db,
        device,
        {"status": "retired", "is_active": False},
    )
    db.commit()
    db.refresh(device)
    return device


def record_heartbeat(
    db: Session,
    device: InfrastructureDevice,
    payload: DeviceHeartbeatRequest,
    *,
    actor: User,
) -> InfrastructureDevice:
    ensure_manager(actor)

    if not device.is_active or device.status == "retired":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Infrastructure device is retired or inactive and cannot accept heartbeats.",
        )
    health_metrics = dict(device.health_metrics or {})
    health_metrics.update(payload.health_metrics)

    repository.update_device(
        db,
        device,
        {
            "status": payload.status.value,
            "health_metrics": health_metrics,
            "last_seen_at": datetime.now(timezone.utc),
        },
    )
    db.commit()
    db.refresh(device)
    return device


def _location_summary(location: GISLocation | None) -> InfrastructureLocationSummary | None:
    if location is None:
        return None
    return InfrastructureLocationSummary(
        id=location.id,
        name=location.name,
        code=location.code,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        zone_id=location.zone_id,
    )


def _device_summary(device: InfrastructureDevice | None) -> DeviceSummary | None:
    if device is None:
        return None
    return DeviceSummary(
        id=device.id,
        device_identifier=device.device_identifier,
        name=device.name,
        device_type=device.device_type,
        role=device.role,
        status=device.status,
        gis_location_id=device.gis_location_id,
    )


def to_read(
    device: InfrastructureDevice,
    *,
    actor: User,
) -> InfrastructureDeviceRead:
    can_manage = bool(actor.is_superuser)
    return InfrastructureDeviceRead(
        id=device.id,
        device_identifier=device.device_identifier,
        name=device.name,
        description=device.description,
        device_type=device.device_type,
        role=device.role,
        gis_location_id=device.gis_location_id,
        location=_location_summary(device.location),
        parent_device_id=device.parent_device_id,
        parent_device=_device_summary(device.parent_device),
        ip_address=device.ip_address if can_manage else None,
        mac_address=device.mac_address if can_manage else None,
        hostname=device.hostname if can_manage else None,
        manufacturer=device.manufacturer,
        model=device.model,
        serial_number=device.serial_number if can_manage else None,
        configuration=dict(device.configuration or {}) if can_manage else {},
        health_metrics=dict(device.health_metrics or {}),
        status=device.status,
        is_active=bool(device.is_active),
        installed_at=device.installed_at,
        last_seen_at=device.last_seen_at,
        created_by_id=device.created_by_id,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def list_response(
    items: list[InfrastructureDevice],
    total: int,
    page: int,
    page_size: int,
    *,
    actor: User,
) -> InfrastructureDeviceListResponse:
    pages = math.ceil(total / page_size) if total else 0
    return InfrastructureDeviceListResponse(
        items=[to_read(item, actor=actor) for item in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
        can_manage=bool(actor.is_superuser),
    )


def summary(
    db: Session,
    *,
    actor: User,
) -> InfrastructureDeviceSummaryResponse:
    statuses = repository.status_counts(db)
    types = repository.type_counts(db)
    return InfrastructureDeviceSummaryResponse(
        total_devices=repository.total_count(db),
        active_devices=repository.active_count(db),
        online_devices=statuses.get("online", 0),
        degraded_devices=statuses.get("degraded", 0),
        offline_devices=statuses.get("offline", 0),
        type_counts=types,
        status_counts=statuses,
        can_manage=bool(actor.is_superuser),
        generated_at=datetime.now(timezone.utc),
    )
