from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.devices import repository, service
from app.modules.devices.schemas import (
    DeviceHeartbeatRequest,
    DeviceRole,
    DeviceStatus,
    DeviceType,
    InfrastructureDeviceCreate,
    InfrastructureDeviceListResponse,
    InfrastructureDeviceRead,
    InfrastructureDeviceSummaryResponse,
    InfrastructureDeviceUpdate,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/devices",
    tags=["Camera & Device Management"],
)


@router.get(
    "/summary",
    response_model=InfrastructureDeviceSummaryResponse,
)
def get_device_summary(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceSummaryResponse:
    return service.summary(db, actor=actor)


@router.get(
    "",
    response_model=InfrastructureDeviceListResponse,
)
def list_devices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    device_type: DeviceType | None = None,
    role: DeviceRole | None = None,
    status: DeviceStatus | None = None,
    gis_location_id: int | None = Query(default=None, ge=1),
    active_only: bool = True,
    search: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceListResponse:
    items, total = repository.list_devices(
        db,
        page=page,
        page_size=page_size,
        device_type=device_type.value if device_type else None,
        role=role.value if role else None,
        status=status.value if status else None,
        gis_location_id=gis_location_id,
        active_only=active_only,
        search=search,
    )
    return service.list_response(
        items,
        total,
        page,
        page_size,
        actor=actor,
    )


@router.post(
    "",
    response_model=InfrastructureDeviceRead,
    status_code=201,
)
def create_device(
    payload: InfrastructureDeviceCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceRead:
    device = service.create_device(db, payload, actor=actor)
    return service.to_read(device, actor=actor)


@router.get(
    "/{device_id}",
    response_model=InfrastructureDeviceRead,
)
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceRead:
    device = service.get_device_or_404(db, device_id)
    return service.to_read(device, actor=actor)


@router.patch(
    "/{device_id}",
    response_model=InfrastructureDeviceRead,
)
def update_device(
    device_id: int,
    payload: InfrastructureDeviceUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceRead:
    device = service.get_device_or_404(db, device_id)
    device = service.update_device(db, device, payload, actor=actor)
    return service.to_read(device, actor=actor)


@router.delete(
    "/{device_id}",
    response_model=InfrastructureDeviceRead,
)
def retire_device(
    device_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceRead:
    device = service.get_device_or_404(db, device_id)
    device = service.retire_device(db, device, actor=actor)
    return service.to_read(device, actor=actor)


@router.post(
    "/{device_id}/heartbeat",
    response_model=InfrastructureDeviceRead,
)
def record_heartbeat(
    device_id: int,
    payload: DeviceHeartbeatRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> InfrastructureDeviceRead:
    device = service.get_device_or_404(db, device_id)
    device = service.record_heartbeat(db, device, payload, actor=actor)
    return service.to_read(device, actor=actor)
