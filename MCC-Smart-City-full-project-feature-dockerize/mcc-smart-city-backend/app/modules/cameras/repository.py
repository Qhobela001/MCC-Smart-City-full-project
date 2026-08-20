from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.cameras.models import Camera


def get_camera(db: Session, camera_id: int) -> Camera | None:
    return db.scalar(select(Camera).where(Camera.id == camera_id))


def get_by_identifier(db: Session, camera_identifier: str) -> Camera | None:
    return db.scalar(
        select(Camera).where(Camera.camera_identifier == camera_identifier)
    )


def get_by_mac(db: Session, mac_address: str) -> Camera | None:
    return db.scalar(select(Camera).where(Camera.mac_address == mac_address))


def get_by_serial(db: Session, serial_number: str) -> Camera | None:
    return db.scalar(
        select(Camera).where(Camera.serial_number == serial_number)
    )


def get_by_v380_device_id(
    db: Session,
    v380_device_id: int,
) -> Camera | None:
    return db.scalar(
        select(Camera).where(
            Camera.v380_device_id == v380_device_id
        )
    )


def list_cameras(
    db: Session,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    stream_status: str | None = None,
    gis_location_id: int | None = None,
    assigned_jetson_id: int | None = None,
    ai_enabled: bool | None = None,
    active_only: bool = True,
    search: str | None = None,
) -> tuple[list[Camera], int]:
    statement = select(Camera)
    count_statement = select(func.count(Camera.id))
    filters = []

    if status is not None:
        filters.append(Camera.status == status)
    if stream_status is not None:
        filters.append(Camera.stream_status == stream_status)
    if gis_location_id is not None:
        filters.append(Camera.gis_location_id == gis_location_id)
    if assigned_jetson_id is not None:
        filters.append(Camera.assigned_jetson_id == assigned_jetson_id)
    if ai_enabled is not None:
        filters.append(Camera.ai_enabled.is_(ai_enabled))
    if active_only:
        filters.append(Camera.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Camera.camera_identifier.ilike(pattern),
                Camera.name.ilike(pattern),
                Camera.ip_address.ilike(pattern),
                Camera.manufacturer.ilike(pattern),
                Camera.model.ilike(pattern),
            )
        )

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(
            statement
            .order_by(Camera.name.asc(), Camera.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().all()
    )
    return items, total


def create_camera(db: Session, values: dict) -> Camera:
    camera = Camera(**values)
    db.add(camera)
    db.flush()
    return camera


def update_camera(db: Session, camera: Camera, values: dict) -> Camera:
    for key, value in values.items():
        setattr(camera, key, value)
    db.add(camera)
    db.flush()
    return camera


def status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Camera.status, func.count(Camera.id)).group_by(Camera.status)
    ).all()
    return {str(status): int(total) for status, total in rows}


def stream_status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(Camera.stream_status, func.count(Camera.id)).group_by(Camera.stream_status)
    ).all()
    return {str(stream_status): int(total) for stream_status, total in rows}


def total_count(db: Session) -> int:
    return int(db.scalar(select(func.count(Camera.id))) or 0)


def active_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(Camera.id)).where(Camera.is_active.is_(True))
        )
        or 0
    )


def ai_enabled_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(Camera.id)).where(
                Camera.is_active.is_(True),
                Camera.ai_enabled.is_(True),
            )
        )
        or 0
    )


def mapped_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(Camera.id)).where(
                Camera.is_active.is_(True),
                Camera.gis_location_id.is_not(None),
            )
        )
        or 0
    )
