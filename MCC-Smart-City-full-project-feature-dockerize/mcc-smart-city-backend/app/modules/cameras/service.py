from __future__ import annotations

import math
import re
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.cameras import repository
from app.modules.cameras.models import Camera
from app.modules.cameras.schemas import (
    CameraCreate,
    CameraHeartbeatRequest,
    CameraListResponse,
    CameraOptionsResponse,
    CameraRead,
    CameraResolveResponse,
    CameraSummaryResponse,
    CameraUpdate,
    DeviceOption,
    LocationOption,
)
from app.modules.devices import repository as device_repository
from app.modules.devices.models import InfrastructureDevice
from app.modules.devices.schemas import (
    DeviceSummary,
    InfrastructureLocationSummary,
)
from app.modules.gis.models import GISLocation
from app.modules.users.models import User


def normalize_identifier(
    value: str,
    *,
    http_error: bool = True,
) -> str:
    normalized = re.sub(
        r"[^A-Z0-9]+",
        "-",
        value.strip().upper(),
    ).strip("-")

    if normalized:
        return normalized

    if http_error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Camera identifier cannot be empty.",
        )
    return ""


def ensure_manager(actor: User) -> None:
    if actor.is_superuser:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Only the Super Administrator can modify camera infrastructure.",
    )


def _active_location(
    db: Session,
    location_id: int | None,
) -> GISLocation | None:
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


def _device_for_assignment(
    db: Session,
    device_id: int | None,
    *,
    expected_type: str,
    expected_role: str | None = None,
    label: str,
) -> InfrastructureDevice | None:
    if device_id is None:
        return None

    device = device_repository.get_device(db, device_id)
    if device is None or not device.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Selected {label} does not exist or is inactive.",
        )
    if device.device_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Selected {label} must be a {expected_type}.",
        )
    if expected_role is not None and device.role != expected_role:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Selected {label} must use the "
                f"{expected_role.replace('_', ' ')} role."
            ),
        )
    return device


def _validate_field_nanostation_link(
    db: Session,
    device: InfrastructureDevice | None,
    *,
    camera_location_id: int | None,
    exclude_camera_id: int | None = None,
) -> None:
    if device is None:
        return

    # One field radio represents one active camera site in the current MCC
    # architecture. Retired cameras do not block later redeployment.
    statement = select(Camera).where(
        Camera.field_nanostation_id == device.id,
        Camera.is_active.is_(True),
    )
    if exclude_camera_id is not None:
        statement = statement.where(Camera.id != exclude_camera_id)

    existing_camera = db.scalar(statement.limit(1))
    if existing_camera is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Selected field NanoStation is already assigned to active "
                f"camera {existing_camera.camera_identifier}."
            ),
        )

    # If both sides are mapped, they must describe the same physical field site.
    if (
        camera_location_id is not None
        and device.gis_location_id is not None
        and device.gis_location_id != camera_location_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Camera and field NanoStation must use the same GIS location "
                "when both are mapped."
            ),
        )


def _duplicate_conflict(
    db: Session,
    *,
    camera_identifier: str | None = None,
    mac_address: str | None = None,
    serial_number: str | None = None,
    exclude_id: int | None = None,
) -> None:
    candidates: list[tuple[Camera | None, str]] = []

    if camera_identifier:
        candidates.append(
            (repository.get_by_identifier(db, camera_identifier), "camera identifier")
        )
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
            detail=f"Another camera already uses this {label}.",
        )


def create_camera(
    db: Session,
    payload: CameraCreate,
    *,
    actor: User,
) -> Camera:
    ensure_manager(actor)

    identifier = normalize_identifier(payload.camera_identifier)
    _active_location(db, payload.gis_location_id)
    _device_for_assignment(
        db,
        payload.assigned_jetson_id,
        expected_type="jetson",
        label="Jetson",
    )
    field_nanostation = _device_for_assignment(
        db,
        payload.field_nanostation_id,
        expected_type="nanostation",
        expected_role="field_radio",
        label="field NanoStation",
    )
    _validate_field_nanostation_link(
        db,
        field_nanostation,
        camera_location_id=payload.gis_location_id,
    )

    _duplicate_conflict(
        db,
        camera_identifier=identifier,
        mac_address=payload.mac_address,
        serial_number=payload.serial_number,
    )

    values = payload.model_dump()
    values["camera_identifier"] = identifier
    values["status"] = payload.status.value
    values["stream_status"] = payload.stream_status.value
    values["created_by_id"] = actor.id

    try:
        camera = repository.create_camera(db, values)
        db.commit()
        db.refresh(camera)
        return camera
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera could not be created because a unique value already exists.",
        ) from exc


def get_camera_or_404(db: Session, camera_id: int) -> Camera:
    camera = repository.get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found.",
        )
    return camera


def get_camera_by_identifier_or_404(
    db: Session,
    camera_identifier: str,
) -> Camera:
    identifier = normalize_identifier(camera_identifier)
    camera = repository.get_by_identifier(db, identifier)

    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registered camera not found.",
        )
    return camera


def update_camera(
    db: Session,
    camera: Camera,
    payload: CameraUpdate,
    *,
    actor: User,
) -> Camera:
    ensure_manager(actor)
    values = payload.model_dump(exclude_unset=True)

    if values.get("camera_identifier") is not None:
        values["camera_identifier"] = normalize_identifier(
            values["camera_identifier"]
        )
    if values.get("status") is not None:
        values["status"] = values["status"].value
    if values.get("stream_status") is not None:
        values["stream_status"] = values["stream_status"].value

    if "gis_location_id" in values:
        _active_location(db, values["gis_location_id"])
    if "assigned_jetson_id" in values:
        _device_for_assignment(
            db,
            values["assigned_jetson_id"],
            expected_type="jetson",
            label="Jetson",
        )
    if "field_nanostation_id" in values:
        _device_for_assignment(
            db,
            values["field_nanostation_id"],
            expected_type="nanostation",
            expected_role="field_radio",
            label="field NanoStation",
        )

    effective_location_id = values.get(
        "gis_location_id",
        camera.gis_location_id,
    )
    effective_nanostation_id = values.get(
        "field_nanostation_id",
        camera.field_nanostation_id,
    )
    effective_nanostation = _device_for_assignment(
        db,
        effective_nanostation_id,
        expected_type="nanostation",
        expected_role="field_radio",
        label="field NanoStation",
    )
    _validate_field_nanostation_link(
        db,
        effective_nanostation,
        camera_location_id=effective_location_id,
        exclude_camera_id=camera.id,
    )

    _duplicate_conflict(
        db,
        camera_identifier=values.get("camera_identifier", camera.camera_identifier),
        mac_address=values.get("mac_address", camera.mac_address),
        serial_number=values.get("serial_number", camera.serial_number),
        exclude_id=camera.id,
    )

    if values.get("status") == "retired":
        values["is_active"] = False
        values["stream_status"] = "disabled"

    try:
        repository.update_camera(db, camera, values)
        db.commit()
        db.refresh(camera)
        return camera
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera could not be updated because a unique value already exists.",
        ) from exc


def retire_camera(
    db: Session,
    camera: Camera,
    *,
    actor: User,
) -> Camera:
    ensure_manager(actor)

    repository.update_camera(
        db,
        camera,
        {
            "status": "retired",
            "stream_status": "disabled",
            "ai_enabled": False,
            "is_active": False,
        },
    )
    db.commit()
    db.refresh(camera)
    return camera


def record_heartbeat(
    db: Session,
    camera: Camera,
    payload: CameraHeartbeatRequest,
    *,
    actor: User,
) -> Camera:
    ensure_manager(actor)

    if not camera.is_active or camera.status == "retired":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Camera is retired or inactive and cannot accept heartbeats.",
        )

    now = datetime.now(timezone.utc)
    repository.update_camera(
        db,
        camera,
        {
            "status": payload.status.value,
            "stream_status": payload.stream_status.value,
            "last_seen_at": now,
            "last_stream_check_at": now,
        },
    )
    db.commit()
    db.refresh(camera)
    return camera


def _location_summary(
    location: GISLocation | None,
) -> InfrastructureLocationSummary | None:
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


def _device_summary(
    device: InfrastructureDevice | None,
) -> DeviceSummary | None:
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
    camera: Camera,
    *,
    actor: User,
) -> CameraRead:
    can_manage = bool(actor.is_superuser)

    return CameraRead(
        id=camera.id,
        camera_identifier=camera.camera_identifier,
        name=camera.name,
        description=camera.description,
        gis_location_id=camera.gis_location_id,
        location=_location_summary(camera.location),
        assigned_jetson_id=camera.assigned_jetson_id,
        assigned_jetson=_device_summary(camera.assigned_jetson),
        field_nanostation_id=camera.field_nanostation_id,
        field_nanostation=_device_summary(camera.field_nanostation),
        ip_address=camera.ip_address if can_manage else None,
        mac_address=camera.mac_address if can_manage else None,
        manufacturer=camera.manufacturer,
        model=camera.model,
        serial_number=camera.serial_number if can_manage else None,
        http_port=camera.http_port if can_manage else None,
        rtsp_port=camera.rtsp_port if can_manage else None,
        rtsp_path=camera.rtsp_path if can_manage else None,
        onvif_port=camera.onvif_port if can_manage else None,
        stream_protocol=camera.stream_protocol,
        credential_reference=(
            camera.credential_reference
            if can_manage
            else None
        ),
        ai_enabled=bool(camera.ai_enabled),
        ai_profile=dict(camera.ai_profile or {}),
        status=camera.status,
        stream_status=camera.stream_status,
        is_active=bool(camera.is_active),
        installed_at=camera.installed_at,
        last_seen_at=camera.last_seen_at,
        last_stream_check_at=camera.last_stream_check_at,
        created_by_id=camera.created_by_id,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


def list_response(
    items: list[Camera],
    total: int,
    page: int,
    page_size: int,
    *,
    actor: User,
) -> CameraListResponse:
    pages = math.ceil(total / page_size) if total else 0
    return CameraListResponse(
        items=[to_read(camera, actor=actor) for camera in items],
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
) -> CameraSummaryResponse:
    statuses = repository.status_counts(db)
    stream_statuses = repository.stream_status_counts(db)

    return CameraSummaryResponse(
        total_cameras=repository.total_count(db),
        active_cameras=repository.active_count(db),
        online_cameras=statuses.get("online", 0),
        degraded_cameras=statuses.get("degraded", 0),
        offline_cameras=statuses.get("offline", 0),
        ai_enabled_cameras=repository.ai_enabled_count(db),
        mapped_cameras=repository.mapped_count(db),
        stream_online_cameras=stream_statuses.get("online", 0),
        status_counts=statuses,
        stream_status_counts=stream_statuses,
        can_manage=bool(actor.is_superuser),
        generated_at=datetime.now(timezone.utc),
    )


def options(
    db: Session,
    *,
    actor: User,
) -> CameraOptionsResponse:
    locations = list(
        db.scalars(
            select(GISLocation)
            .where(GISLocation.is_active.is_(True))
            .order_by(GISLocation.name.asc())
        ).unique().all()
    )

    jetsons = device_repository.list_active_by_type(db, "jetson")
    nanostations = device_repository.list_active_by_type(db, "nanostation")

    return CameraOptionsResponse(
        locations=[
            LocationOption(
                id=location.id,
                name=location.name,
                code=location.code,
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                zone_id=location.zone_id,
            )
            for location in locations
        ],
        jetsons=[
            DeviceOption(
                id=device.id,
                device_identifier=device.device_identifier,
                name=device.name,
                device_type=device.device_type,
                role=device.role,
                status=device.status,
                gis_location_id=device.gis_location_id,
            )
            for device in jetsons
        ],
        nanostations=[
            DeviceOption(
                id=device.id,
                device_identifier=device.device_identifier,
                name=device.name,
                device_type=device.device_type,
                role=device.role,
                status=device.status,
                gis_location_id=device.gis_location_id,
            )
            for device in nanostations
        ],
        can_manage=bool(actor.is_superuser),
    )


def resolve(camera: Camera) -> CameraResolveResponse:
    return CameraResolveResponse(
        camera_id=camera.id,
        camera_identifier=camera.camera_identifier,
        name=camera.name,
        gis_location_id=camera.gis_location_id,
        location=_location_summary(camera.location),
        assigned_jetson=_device_summary(camera.assigned_jetson),
        field_nanostation=_device_summary(camera.field_nanostation),
        ai_enabled=bool(camera.ai_enabled),
        status=camera.status,
    )
