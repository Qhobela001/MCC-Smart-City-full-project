import hmac
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.modules.cameras import repository, service
from app.modules.cameras.schemas import (
    CameraConnectionTestRequest,
    CameraConnectionTestResponse,
    CameraCreate,
    CameraCredentialMigrationResponse,
    CameraGatewayHeartbeatResponse,
    CameraHeartbeatRequest,
    CameraListResponse,
    CameraOptionsResponse,
    CameraRead,
    CameraResolveResponse,
    CameraStatus,
    CameraSummaryResponse,
    CameraUpdate,
    StreamStatus,
)
from app.modules.users.models import User

from app.modules.cameras import integration as _camera_integration  # noqa: F401


router = APIRouter(
    prefix="/cameras",
    tags=["Camera & Device Management"],
)


def require_camera_gateway(
    supplied_key: str | None = Header(
        default=None,
        alias="X-Camera-Gateway-Key",
    ),
) -> None:
    expected_key = os.getenv("CAMERA_GATEWAY_SHARED_KEY", "")
    if (
        not expected_key
        or supplied_key is None
        or not hmac.compare_digest(supplied_key, expected_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Camera gateway authentication failed.",
        )


@router.get(
    "/summary",
    response_model=CameraSummaryResponse,
)
def get_camera_summary(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraSummaryResponse:
    return service.summary(db, actor=actor)


@router.get(
    "/options",
    response_model=CameraOptionsResponse,
)
def get_camera_options(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraOptionsResponse:
    return service.options(db, actor=actor)


@router.get(
    "/resolve/{camera_identifier}",
    response_model=CameraResolveResponse,
)
def resolve_camera_identifier(
    camera_identifier: str,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraResolveResponse:
    camera = service.get_camera_by_identifier_or_404(
        db,
        camera_identifier,
    )
    return service.resolve(camera)


@router.get(
    "",
    response_model=CameraListResponse,
)
def list_cameras(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: CameraStatus | None = None,
    stream_status: StreamStatus | None = None,
    gis_location_id: int | None = Query(default=None, ge=1),
    assigned_jetson_id: int | None = Query(default=None, ge=1),
    ai_enabled: bool | None = None,
    active_only: bool = True,
    search: str | None = Query(default=None, max_length=150),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraListResponse:
    items, total = repository.list_cameras(
        db,
        page=page,
        page_size=page_size,
        status=status.value if status else None,
        stream_status=stream_status.value if stream_status else None,
        gis_location_id=gis_location_id,
        assigned_jetson_id=assigned_jetson_id,
        ai_enabled=ai_enabled,
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
    response_model=CameraRead,
    status_code=201,
)
def create_camera(
    payload: CameraCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraRead:
    camera = service.create_camera(
        db,
        payload,
        actor=actor,
    )
    return service.to_read(camera, actor=actor)


@router.post(
    "/test-connection",
    response_model=CameraConnectionTestResponse,
)
def test_camera_connection(
    payload: CameraConnectionTestRequest,
    actor: User = Depends(get_current_user),
) -> CameraConnectionTestResponse:
    return service.test_camera_connection(payload, actor=actor)


@router.post(
    "/{camera_id}/credentials/migrate",
    response_model=CameraCredentialMigrationResponse,
)
def migrate_camera_credentials(
    camera_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraCredentialMigrationResponse:
    camera = service.get_camera_or_404(db, camera_id)
    return service.migrate_camera_credentials(
        db,
        camera,
        actor=actor,
    )


@router.get(
    "/{camera_id}",
    response_model=CameraRead,
)
def get_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraRead:
    camera = service.get_camera_or_404(db, camera_id)
    return service.to_read(camera, actor=actor)


@router.patch(
    "/{camera_id}",
    response_model=CameraRead,
)
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraRead:
    camera = service.get_camera_or_404(db, camera_id)
    camera = service.update_camera(
        db,
        camera,
        payload,
        actor=actor,
    )
    return service.to_read(camera, actor=actor)


@router.delete(
    "/{camera_id}",
    response_model=CameraRead,
)
def retire_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraRead:
    camera = service.get_camera_or_404(db, camera_id)
    camera = service.retire_camera(
        db,
        camera,
        actor=actor,
    )
    return service.to_read(camera, actor=actor)


@router.post(
    "/gateway/{camera_identifier}/heartbeat",
    response_model=CameraGatewayHeartbeatResponse,
)
def record_gateway_camera_heartbeat(
    camera_identifier: str,
    payload: CameraHeartbeatRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_camera_gateway),
) -> CameraGatewayHeartbeatResponse:
    camera = service.get_camera_by_identifier_or_404(
        db,
        camera_identifier,
    )
    camera = service.record_gateway_heartbeat(db, camera, payload)
    return CameraGatewayHeartbeatResponse(
        camera_id=camera.id,
        camera_identifier=camera.camera_identifier,
        status=CameraStatus(camera.status),
        stream_status=StreamStatus(camera.stream_status),
        last_seen_at=camera.last_seen_at,
        last_stream_check_at=camera.last_stream_check_at,
    )


@router.post(
    "/{camera_id}/heartbeat",
    response_model=CameraRead,
)
def record_camera_heartbeat(
    camera_id: int,
    payload: CameraHeartbeatRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> CameraRead:
    camera = service.get_camera_or_404(db, camera_id)
    camera = service.record_heartbeat(
        db,
        camera,
        payload,
        actor=actor,
    )
    return service.to_read(camera, actor=actor)
