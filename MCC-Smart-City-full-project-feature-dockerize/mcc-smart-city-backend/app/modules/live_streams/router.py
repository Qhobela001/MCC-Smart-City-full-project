import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, require_permission
from app.modules.live_streams import service
from app.modules.live_streams.schemas import (
    CameraGatewayHealthRead,
    CameraPTZRequest,
    CameraPTZResponse,
    GatewayStatusRead,
    GatewayCameraRegistryResponse,
    LiveCameraRead,
    LiveStreamListResponse,
    LiveStreamSessionResponse,
    MediaMTXAuthRequest,
    SyncAllResponse,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/live-streams",
    tags=["Live Monitoring"],
)


@router.post(
    "/mediamtx/auth",
    include_in_schema=False,
    status_code=status.HTTP_204_NO_CONTENT,
)
def authorize_mediamtx_request(
    payload: MediaMTXAuthRequest,
) -> Response:
    if payload.action == "publish":
        expected_user = os.getenv(
            "LIVE_STREAM_PUBLISH_USERNAME",
            "",
        )
        expected_password = os.getenv(
            "LIVE_STREAM_PUBLISH_PASSWORD",
            "",
        )

        if (
            not expected_user
            or not secrets.compare_digest(payload.user, expected_user)
            or not secrets.compare_digest(payload.password, expected_password)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Stream publisher credentials are invalid.",
            )

        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if payload.action != "read":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Stream action is not allowed.",
        )

    if not payload.token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A live-stream token is required.",
        )

    try:
        service.validate_stream_token(
            payload.token,
            requested_path=payload.path,
        )
    except service.StreamTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/gateway/cameras",
    response_model=GatewayCameraRegistryResponse,
    include_in_schema=False,
)
def get_gateway_camera_registry(
    db: Session = Depends(get_db),
    x_camera_gateway_key: str = Header(
        default="",
        alias="X-Camera-Gateway-Key",
    ),
) -> GatewayCameraRegistryResponse:
    expected = os.getenv("CAMERA_GATEWAY_SHARED_KEY", "")
    if (
        not expected
        or not secrets.compare_digest(
            x_camera_gateway_key,
            expected,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Camera gateway authentication failed.",
        )

    return service.list_gateway_camera_configs(db)


@router.get(
    "/camera-gateway/health",
    response_model=CameraGatewayHealthRead,
)
def get_camera_gateway_health(
    actor: User = Depends(require_permission("cameras.view")),
) -> CameraGatewayHealthRead:
    del actor
    return service.camera_gateway_health()


@router.get(
    "/gateway",
    response_model=GatewayStatusRead,
)
def get_gateway_status(
    actor: User = Depends(require_permission("cameras.view")),
) -> GatewayStatusRead:
    del actor
    return service.gateway_status()


@router.get(
    "",
    response_model=LiveStreamListResponse,
)
def list_live_streams(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cameras.view")),
) -> LiveStreamListResponse:
    del actor
    return service.list_live_cameras(db)


@router.post(
    "/sync",
    response_model=SyncAllResponse,
)
def sync_live_streams(
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cameras.manage")),
) -> SyncAllResponse:
    del actor
    return service.sync_all(db)


@router.get(
    "/cameras/{camera_identifier}",
    response_model=LiveCameraRead,
)
def get_live_camera(
    camera_identifier: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cameras.view")),
) -> LiveCameraRead:
    del actor
    try:
        return service.get_live_camera(db, camera_identifier)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.post(
    "/cameras/{camera_identifier}/session",
    response_model=LiveStreamSessionResponse,
)
def create_live_stream_session(
    camera_identifier: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cameras.view")),
) -> LiveStreamSessionResponse:
    try:
        return service.create_session(
            db,
            camera_identifier,
            actor=actor,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except service.StreamNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.GatewayUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except service.StreamTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/cameras/{camera_identifier}/ptz",
    response_model=CameraPTZResponse,
)
def control_camera_ptz(
    camera_identifier: str,
    payload: CameraPTZRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("cameras.manage")),
) -> CameraPTZResponse:
    del actor
    try:
        return service.send_camera_ptz(db, camera_identifier, payload)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except service.PTZControlError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except service.GatewayUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
