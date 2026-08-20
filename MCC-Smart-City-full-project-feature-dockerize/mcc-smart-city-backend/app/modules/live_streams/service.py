from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.cameras.models import Camera
from app.modules.cameras import credential_vault
from app.modules.cameras import repository as camera_repository
from app.modules.live_streams.schemas import (
    GatewayStatusRead,
    GatewayCameraConfigRead,
    GatewayCameraRegistryResponse,
    LiveCameraRead,
    LiveStreamListResponse,
    LiveStreamSessionResponse,
    SyncAllResponse,
    SyncFailure,
)
from app.modules.users.models import User


class LiveStreamError(RuntimeError):
    pass


class GatewayUnavailableError(LiveStreamError):
    pass


class StreamNotConfiguredError(LiveStreamError):
    pass


class StreamTokenError(LiveStreamError):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mediamtx_api_url() -> str:
    return os.getenv("MEDIAMTX_API_URL", "http://mediamtx:9997").rstrip("/")


def _mediamtx_webrtc_public_url() -> str:
    return os.getenv(
        "MEDIAMTX_WEBRTC_PUBLIC_URL",
        "http://localhost:8889",
    ).rstrip("/")


def _token_ttl_seconds() -> int:
    raw = os.getenv("LIVE_STREAM_TOKEN_TTL_SECONDS", "300")
    try:
        return max(30, min(int(raw), 3600))
    except ValueError:
        return 300


def _token_secret() -> bytes:
    secret = (
        os.getenv("LIVE_STREAM_TOKEN_SECRET")
        or getattr(settings, "SECRET_KEY", None)
        or getattr(settings, "JWT_SECRET", None)
        or getattr(settings, "JWT_SECRET_KEY", None)
    )
    if not secret:
        raise StreamTokenError(
            "Live-stream token secret is not configured."
        )
    return str(secret).encode("utf-8")


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def gateway_path_for(camera_identifier: str) -> str:
    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        camera_identifier.strip().lower(),
    ).strip("-")
    if not normalized:
        raise StreamNotConfiguredError("Camera identifier is invalid.")
    return normalized


def _location_values(camera: Camera) -> tuple[str | None, float | None, float | None]:
    location = getattr(camera, "location", None)
    if location is None:
        return None, None, None

    latitude = getattr(location, "latitude", None)
    longitude = getattr(location, "longitude", None)

    return (
        getattr(location, "name", None),
        float(latitude) if latitude is not None else None,
        float(longitude) if longitude is not None else None,
    )


def _stream_protocol(camera: Camera) -> str:
    return (camera.stream_protocol or "rtsp").strip().lower()


def _stream_path_value(camera: Camera) -> str:
    return (camera.rtsp_path or "").strip().strip("/")


V380_PROTOCOLS = {"v380", "v380-legacy", "macrovideo"}


def _is_v380_camera(camera: Camera) -> bool:
    protocol = _stream_protocol(camera)
    if protocol in V380_PROTOCOLS:
        return True

    # Temporary backwards compatibility for camera rows created before
    # dedicated V380 fields existed. Once all deployed rows are migrated and
    # the Camera Management UI writes stream_protocol=v380 explicitly, this
    # fallback can be removed.
    path = _stream_path_value(camera)
    return (camera.rtsp_port or 0) == 8800 and path.isdigit()


def _v380_port(camera: Camera) -> int | None:
    dedicated = getattr(camera, "v380_port", None)
    if dedicated is not None:
        value = int(dedicated)
        if 1 <= value <= 65535:
            return value
        return None

    # Temporary compatibility with the pre-Stage-1 schema.
    fallback = camera.rtsp_port
    if fallback is None:
        return 8800 if _stream_protocol(camera) in V380_PROTOCOLS else None

    value = int(fallback)
    return value if 1 <= value <= 65535 else None


def _v380_device_id(camera: Camera) -> int | None:
    dedicated = getattr(camera, "v380_device_id", None)
    if dedicated is not None:
        value = int(dedicated)
        return value if value > 0 else None

    # Temporary compatibility with rows where rtsp_path carried the V380
    # numeric device ID.
    path = _stream_path_value(camera)
    if not path.isdigit():
        return None
    value = int(path)
    return value if value > 0 else None


def _is_stream_configured(camera: Camera) -> bool:
    if (
        not camera.is_active
        or not camera.ip_address
        or camera.stream_status == "disabled"
    ):
        return False

    if _is_v380_camera(camera):
        return (
            _v380_port(camera) is not None
            and _v380_device_id(camera) is not None
        )

    protocol = _stream_protocol(camera)
    return bool(
        camera.rtsp_path
        and protocol in {"rtsp", "rtsps"}
    )


def _camera_read(
    camera: Camera,
    *,
    path_state: dict[str, Any] | None = None,
) -> LiveCameraRead:
    location_name, latitude, longitude = _location_values(camera)
    jetson = getattr(camera, "assigned_jetson", None)
    radio = getattr(camera, "field_nanostation", None)

    readers = []
    if path_state:
        raw_readers = path_state.get("readers")
        if isinstance(raw_readers, list):
            readers = raw_readers

    return LiveCameraRead(
        camera_id=camera.id,
        camera_identifier=camera.camera_identifier,
        name=camera.name,
        gis_location_id=camera.gis_location_id,
        location_name=location_name,
        latitude=latitude,
        longitude=longitude,
        status=str(camera.status),
        stream_status=(
            "online"
            if path_state is not None and bool(path_state.get("ready"))
            else (
                "offline"
                if _is_v380_camera(camera)
                else str(camera.stream_status)
            )
        ),
        ai_enabled=bool(camera.ai_enabled),
        is_active=bool(camera.is_active),
        assigned_jetson_identifier=(
            getattr(jetson, "device_identifier", None) if jetson else None
        ),
        assigned_jetson_name=(getattr(jetson, "name", None) if jetson else None),
        field_nanostation_identifier=(
            getattr(radio, "device_identifier", None) if radio else None
        ),
        stream_configured=_is_stream_configured(camera),
        gateway_path=gateway_path_for(camera.camera_identifier),
        gateway_ready=(
            bool(path_state.get("ready")) if path_state is not None else None
        ),
        viewer_count=len(readers),
        last_seen_at=camera.last_seen_at,
        last_stream_check_at=camera.last_stream_check_at,
    )


def _control_request(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 4.0,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}

    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        f"{_mediamtx_api_url()}{path}",
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except HTTPError:
        raise
    except (URLError, TimeoutError, OSError) as exc:
        raise GatewayUnavailableError(
            "The MCC live-stream gateway is unavailable."
        ) from exc


def gateway_status() -> GatewayStatusRead:
    available = True
    try:
        _control_request("GET", "/v3/info")
    except (GatewayUnavailableError, HTTPError, ValueError, json.JSONDecodeError):
        available = False

    return GatewayStatusRead(
        available=available,
        generated_at=_utcnow(),
    )


def _path_states() -> tuple[bool, dict[str, dict[str, Any]]]:
    try:
        response = _control_request("GET", "/v3/paths/list")
    except (GatewayUnavailableError, HTTPError, ValueError, json.JSONDecodeError):
        return False, {}

    items = response.get("items", [])
    if not isinstance(items, list):
        items = []

    states: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str):
            states[name] = item
    return True, states


def list_live_cameras(db: Session) -> LiveStreamListResponse:
    cameras = list(
        db.scalars(
            select(Camera)
            .where(Camera.is_active.is_(True))
            .order_by(Camera.name.asc(), Camera.id.asc())
        ).unique().all()
    )

    gateway_available, states = _path_states()
    items = [
        _camera_read(
            camera,
            path_state=states.get(gateway_path_for(camera.camera_identifier)),
        )
        for camera in cameras
    ]

    return LiveStreamListResponse(
        items=items,
        total=len(items),
        gateway_available=gateway_available,
        generated_at=_utcnow(),
    )


def get_live_camera(db: Session, camera_identifier: str) -> LiveCameraRead:
    camera = camera_repository.get_by_identifier(db, camera_identifier)
    if camera is None:
        raise LookupError("Camera not found.")

    _, states = _path_states()
    path = gateway_path_for(camera.camera_identifier)
    return _camera_read(camera, path_state=states.get(path))


def _credential_value(
    db: Session,
    camera: Camera,
) -> tuple[str, str] | None:
    try:
        return credential_vault.resolve_credentials(
            db,
            camera,
        )
    except credential_vault.CredentialVaultError as exc:
        raise StreamNotConfiguredError(str(exc)) from exc


def _camera_source_url(
    db: Session,
    camera: Camera,
) -> str:
    if not _is_stream_configured(camera):
        raise StreamNotConfiguredError(
            "Camera RTSP stream is not configured in Camera & Device Management."
        )

    protocol = _stream_protocol(camera)
    if protocol not in {"rtsp", "rtsps"}:
        raise StreamNotConfiguredError(
            "Live Monitoring currently supports RTSP/RTSPS camera sources."
        )

    path = (camera.rtsp_path or "").strip()
    if not path.startswith("/"):
        path = f"/{path}"

    port = camera.rtsp_port or 554
    authority = str(camera.ip_address)

    credentials = _credential_value(db, camera)
    if credentials:
        username, password = credentials
        authority = (
            f"{quote(username, safe='')}:{quote(password, safe='')}@{authority}"
        )

    return f"{protocol}://{authority}:{port}{path}"


def sync_camera(
    db: Session,
    camera: Camera,
) -> str:
    path = gateway_path_for(camera.camera_identifier)

    # V380 cameras are push sources. The persistent camera-gateway service
    # publishes them into this path, therefore FastAPI must not configure
    # MediaMTX to pull RTSP directly from the camera.
    if _is_v380_camera(camera):
        if not _is_stream_configured(camera):
            raise StreamNotConfiguredError(
                "V380 camera requires an IP address, V380 port and numeric device ID."
            )
        return path

    source_url = _camera_source_url(db, camera)
    encoded_path = quote(path, safe="")

    payload = {
        "source": source_url,
        "sourceOnDemand": False,
        "rtspTransport": "tcp",
        "record": False,
    }

    try:
        _control_request(
            "POST",
            f"/v3/config/paths/replace/{encoded_path}",
            payload,
        )
    except HTTPError as exc:
        if exc.code != 404:
            raise GatewayUnavailableError(
                "The live-stream gateway rejected the camera configuration."
            ) from exc
        try:
            _control_request(
                "POST",
                f"/v3/config/paths/add/{encoded_path}",
                payload,
            )
        except HTTPError as add_exc:
            raise GatewayUnavailableError(
                "The live-stream gateway could not register the camera path."
            ) from add_exc

    return path


def sync_all(db: Session) -> SyncAllResponse:
    cameras = list(
        db.scalars(
            select(Camera)
            .where(Camera.is_active.is_(True))
            .order_by(Camera.camera_identifier.asc())
        ).unique().all()
    )

    synced: list[str] = []
    skipped: list[str] = []
    failed: list[SyncFailure] = []

    for camera in cameras:
        if not _is_stream_configured(camera):
            skipped.append(camera.camera_identifier)
            continue

        try:
            sync_camera(db, camera)
            synced.append(camera.camera_identifier)
        except LiveStreamError as exc:
            failed.append(
                SyncFailure(
                    camera_identifier=camera.camera_identifier,
                    reason=str(exc),
                )
            )

    return SyncAllResponse(
        synced=synced,
        skipped=skipped,
        failed=failed,
        gateway_available=gateway_status().available,
        generated_at=_utcnow(),
    )



def _v380_credentials(
    db: Session,
    camera: Camera,
) -> tuple[str, str]:
    credentials = _credential_value(db, camera)
    if credentials is not None:
        return credentials

    return (
        os.getenv("V380_DEFAULT_USERNAME", "admin"),
        os.getenv("V380_DEFAULT_PASSWORD", ""),
    )


def list_gateway_camera_configs(
    db: Session,
) -> GatewayCameraRegistryResponse:
    cameras = list(
        db.scalars(
            select(Camera)
            .where(Camera.is_active.is_(True))
            .order_by(Camera.camera_identifier.asc())
        ).unique().all()
    )

    items: list[GatewayCameraConfigRead] = []
    for camera in cameras:
        if not _is_v380_camera(camera):
            continue
        if not _is_stream_configured(camera):
            continue

        device_id = _v380_device_id(camera)
        if device_id is None:
            continue

        username, password = _v380_credentials(db, camera)
        items.append(
            GatewayCameraConfigRead(
                camera_identifier=camera.camera_identifier,
                gateway_path=gateway_path_for(camera.camera_identifier),
                host=str(camera.ip_address),
                port=int(_v380_port(camera) or 8800),
                device_id=device_id,
                username=username,
                password=password,
                enabled=(
                    camera.is_active
                    and camera.stream_status != "disabled"
                ),
            )
        )

    return GatewayCameraRegistryResponse(
        items=items,
        total=len(items),
        generated_at=_utcnow(),
    )

def _issue_stream_token(
    *,
    actor: User,
    camera: Camera,
    path: str,
) -> tuple[str, datetime]:
    expires_at = _utcnow() + timedelta(seconds=_token_ttl_seconds())
    payload = {
        "v": 1,
        "sub": str(actor.id),
        "camera_id": camera.id,
        "camera_identifier": camera.camera_identifier,
        "path": path,
        "action": "read",
        "exp": int(expires_at.timestamp()),
        "nonce": secrets.token_urlsafe(12),
    }

    encoded_payload = _b64url_encode(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    )
    signature = hmac.new(
        _token_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return f"{encoded_payload}.{_b64url_encode(signature)}", expires_at


def validate_stream_token(token: str, *, requested_path: str) -> dict[str, Any]:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
    except ValueError as exc:
        raise StreamTokenError("Malformed stream token.") from exc

    expected_signature = hmac.new(
        _token_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    try:
        supplied_signature = _b64url_decode(encoded_signature)
    except Exception as exc:
        raise StreamTokenError("Malformed stream token signature.") from exc

    if not hmac.compare_digest(expected_signature, supplied_signature):
        raise StreamTokenError("Invalid stream token signature.")

    try:
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise StreamTokenError("Malformed stream token payload.") from exc

    if payload.get("action") != "read":
        raise StreamTokenError("Stream token action is invalid.")
    if payload.get("path") != requested_path:
        raise StreamTokenError("Stream token does not match this camera path.")

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int) or expires_at <= int(_utcnow().timestamp()):
        raise StreamTokenError("Stream token has expired.")

    return payload


def create_session(
    db: Session,
    camera_identifier: str,
    *,
    actor: User,
) -> LiveStreamSessionResponse:
    camera = camera_repository.get_by_identifier(db, camera_identifier)
    if camera is None:
        raise LookupError("Camera not found.")

    if not camera.is_active or camera.status == "retired":
        raise StreamNotConfiguredError("Camera is not active.")
    if camera.stream_status == "disabled":
        raise StreamNotConfiguredError("Camera live stream is disabled.")

    path = sync_camera(db, camera)
    token, expires_at = _issue_stream_token(
        actor=actor,
        camera=camera,
        path=path,
    )

    try:
        state = _control_request(
            "GET",
            f"/v3/paths/get/{quote(path, safe='')}",
            timeout=2.5,
        )
    except (GatewayUnavailableError, HTTPError, ValueError, json.JSONDecodeError):
        state = None

    whep_url = urljoin(
        f"{_mediamtx_webrtc_public_url()}/",
        f"{path}/whep",
    )

    return LiveStreamSessionResponse(
        camera=_camera_read(camera, path_state=state),
        gateway_path=path,
        whep_url=whep_url,
        token=token,
        expires_at=expires_at,
    )
