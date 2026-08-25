from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.devices.models import InfrastructureDevice


def get_device(db: Session, device_id: int) -> InfrastructureDevice | None:
    return db.scalar(select(InfrastructureDevice).where(InfrastructureDevice.id == device_id))


def get_by_identifier(db: Session, device_identifier: str) -> InfrastructureDevice | None:
    return db.scalar(
        select(InfrastructureDevice).where(
            InfrastructureDevice.device_identifier == device_identifier
        )
    )


def get_by_mac(db: Session, mac_address: str) -> InfrastructureDevice | None:
    return db.scalar(
        select(InfrastructureDevice).where(
            InfrastructureDevice.mac_address == mac_address
        )
    )


def get_by_serial(db: Session, serial_number: str) -> InfrastructureDevice | None:
    return db.scalar(
        select(InfrastructureDevice).where(
            InfrastructureDevice.serial_number == serial_number
        )
    )


def list_devices(
    db: Session,
    *,
    page: int,
    page_size: int,
    device_type: str | None = None,
    role: str | None = None,
    status: str | None = None,
    gis_location_id: int | None = None,
    active_only: bool = True,
    search: str | None = None,
) -> tuple[list[InfrastructureDevice], int]:
    statement = select(InfrastructureDevice)
    count_statement = select(func.count(InfrastructureDevice.id))
    filters = []

    if device_type is not None:
        filters.append(InfrastructureDevice.device_type == device_type)
    if role is not None:
        filters.append(InfrastructureDevice.role == role)
    if status is not None:
        filters.append(InfrastructureDevice.status == status)
    if gis_location_id is not None:
        filters.append(InfrastructureDevice.gis_location_id == gis_location_id)
    if active_only:
        filters.append(InfrastructureDevice.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                InfrastructureDevice.device_identifier.ilike(pattern),
                InfrastructureDevice.name.ilike(pattern),
                InfrastructureDevice.hostname.ilike(pattern),
                InfrastructureDevice.ip_address.ilike(pattern),
                InfrastructureDevice.manufacturer.ilike(pattern),
                InfrastructureDevice.model.ilike(pattern),
            )
        )

    if filters:
        statement = statement.where(*filters)
        count_statement = count_statement.where(*filters)

    total = int(db.scalar(count_statement) or 0)
    items = list(
        db.scalars(
            statement
            .order_by(
                InfrastructureDevice.device_type.asc(),
                InfrastructureDevice.name.asc(),
                InfrastructureDevice.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).unique().all()
    )
    return items, total


def list_active_by_type(db: Session, device_type: str) -> list[InfrastructureDevice]:
    statement = (
        select(InfrastructureDevice)
        .where(
            InfrastructureDevice.device_type == device_type,
            InfrastructureDevice.is_active.is_(True),
            InfrastructureDevice.status != "retired",
        )
        .order_by(InfrastructureDevice.name.asc(), InfrastructureDevice.id.asc())
    )
    return list(db.scalars(statement).unique().all())


def list_active_children(db: Session, parent_device_id: int) -> list[InfrastructureDevice]:
    statement = select(InfrastructureDevice).where(
        InfrastructureDevice.parent_device_id == parent_device_id,
        InfrastructureDevice.is_active.is_(True),
    )
    return list(db.scalars(statement).unique().all())


def create_device(db: Session, values: dict) -> InfrastructureDevice:
    device = InfrastructureDevice(**values)
    db.add(device)
    db.flush()
    return device


def update_device(
    db: Session,
    device: InfrastructureDevice,
    values: dict,
) -> InfrastructureDevice:
    for key, value in values.items():
        setattr(device, key, value)
    db.add(device)
    db.flush()
    return device


def status_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(
            InfrastructureDevice.status,
            func.count(InfrastructureDevice.id),
        ).group_by(InfrastructureDevice.status)
    ).all()
    return {str(status): int(total) for status, total in rows}


def type_counts(db: Session) -> dict[str, int]:
    rows = db.execute(
        select(
            InfrastructureDevice.device_type,
            func.count(InfrastructureDevice.id),
        ).group_by(InfrastructureDevice.device_type)
    ).all()
    return {str(device_type): int(total) for device_type, total in rows}


def total_count(db: Session) -> int:
    return int(db.scalar(select(func.count(InfrastructureDevice.id))) or 0)


def active_count(db: Session) -> int:
    return int(
        db.scalar(
            select(func.count(InfrastructureDevice.id)).where(
                InfrastructureDevice.is_active.is_(True)
            )
        )
        or 0
    )
