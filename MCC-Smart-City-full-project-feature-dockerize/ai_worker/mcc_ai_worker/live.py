from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Protocol

from .config import LiveConfig, WorkerConfig
from .ingestion import IngestionClient, IngestionError
from .model import MCCModel
from .payloads import build_live_detection
from .runner import write_health


@dataclass(frozen=True)
class StreamSession:
    gateway_path: str
    token: str
    expires_at: datetime


class Capture(Protocol):
    def isOpened(self) -> bool: ...
    def read(self) -> tuple[bool, object]: ...
    def release(self) -> None: ...


class LiveSessionClient:
    def __init__(self, url_template: str, worker_key: str) -> None:
        self.url_template = url_template
        self.worker_key = worker_key

    def create(self, camera_identifier: str) -> StreamSession:
        url = self.url_template.format(
            camera_identifier=urllib.parse.quote(camera_identifier, safe="")
        )
        request = urllib.request.Request(
            url,
            data=b"",
            method="POST",
            headers={"X-AI-Worker-Key": self.worker_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"AI stream session rejected ({exc.code}): {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(f"AI stream session unavailable: {exc}") from exc

        expires = str(payload["expires_at"]).replace("Z", "+00:00")
        return StreamSession(
            gateway_path=str(payload["gateway_path"]),
            token=str(payload["token"]),
            expires_at=datetime.fromisoformat(expires).astimezone(timezone.utc),
        )


def authenticated_rtsp_url(base_url: str, session: StreamSession) -> str:
    token = urllib.parse.quote(session.token, safe="")
    path = urllib.parse.quote(session.gateway_path.strip("/"), safe="/")
    return f"{base_url}/{path}?jwt={token}"


def default_capture_factory(url: str) -> Capture:
    os.environ.setdefault(
        "OPENCV_FFMPEG_CAPTURE_OPTIONS",
        "rtsp_transport;tcp|stimeout;5000000",
    )
    import cv2

    capture = cv2.VideoCapture(
        url,
        cv2.CAP_FFMPEG,
        [
            cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
            5000,
            cv2.CAP_PROP_READ_TIMEOUT_MSEC,
            5000,
        ],
    )
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    return capture


def _health(counters: dict, **changes: object) -> dict:
    counters.update(changes)
    return dict(counters)


def run_live_observer(
    worker: WorkerConfig,
    live: LiveConfig,
    *,
    model: MCCModel | None = None,
    ingestion: IngestionClient | None = None,
    sessions: LiveSessionClient | None = None,
    capture_factory: Callable[[str], Capture] = default_capture_factory,
    stop_event: threading.Event | None = None,
    max_runtime_seconds: float | None = None,
    max_frames_analyzed: int | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    utcnow: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict:
    """Observe one MediaMTX stream sequentially; inference never overlaps."""
    stop_event = stop_event or threading.Event()
    model = model or MCCModel(worker.model_path, worker.model_sha256)
    ingestion = ingestion or IngestionClient(
        worker.backend_url, worker.worker_key, worker.request_attempts
    )
    sessions = sessions or LiveSessionClient(
        live.session_url_template, worker.worker_key
    )
    started_mono = monotonic()
    started_at = utcnow()
    counters = {
        "status": "starting",
        "stage": "AI-2",
        "observation_mode": True,
        "is_test": True,
        "camera_identifier": live.camera_identifier,
        "model_sha256": model.sha256,
        "started_at": started_at.isoformat(),
        "frames_received": 0,
        "frames_analyzed": 0,
        "detections_seen": 0,
        "detections_created": 0,
        "reconnects": 0,
        "consecutive_failures": 0,
        "last_frame_at": None,
        "last_inference_at": None,
        "last_ingestion_at": None,
        "gateway_path": None,
        "failure": None,
    }
    write_health(live.health_path, counters)
    reconnect_delay = live.reconnect_min_seconds
    frame_sequence = 0

    def reached_limit() -> bool:
        if max_frames_analyzed is not None:
            if counters["frames_analyzed"] >= max_frames_analyzed:
                return True
        if max_runtime_seconds is not None:
            return monotonic() - started_mono >= max_runtime_seconds
        return False

    while not stop_event.is_set() and not reached_limit():
        capture: Capture | None = None
        connected = False
        token_refresh = False
        try:
            write_health(
                live.health_path,
                _health(counters, status="connecting", failure=None),
            )
            session = sessions.create(live.camera_identifier)
            capture = capture_factory(authenticated_rtsp_url(live.rtsp_base_url, session))
            if not capture.isOpened():
                raise RuntimeError("MediaMTX RTSP stream could not be opened.")
            connected = True
            reconnect_delay = live.reconnect_min_seconds
            next_sample = monotonic()
            write_health(
                live.health_path,
                _health(
                    counters,
                    status="online",
                    gateway_path=session.gateway_path,
                    consecutive_failures=0,
                    failure=None,
                    connected_at=utcnow().isoformat(),
                ),
            )

            while not stop_event.is_set() and not reached_limit():
                remaining = (session.expires_at - utcnow()).total_seconds()
                if remaining <= live.token_refresh_seconds:
                    token_refresh = True
                    break

                ok, frame = capture.read()
                if not ok:
                    raise RuntimeError("MediaMTX RTSP frame read failed.")
                now = utcnow()
                counters["frames_received"] += 1
                counters["last_frame_at"] = now.isoformat()

                if monotonic() < next_sample:
                    continue

                # This call is synchronous by design: there can be only one
                # inference and one ingestion batch in flight for this worker.
                raw = model.predict(frame, worker.confidence, worker.image_size)
                counters["frames_analyzed"] += 1
                counters["last_inference_at"] = now.isoformat()
                batch = [
                    build_live_detection(
                        detection=item,
                        captured_at=now,
                        camera_identifier=live.camera_identifier,
                        gateway_path=session.gateway_path,
                        frame_sequence=frame_sequence,
                        model_name=worker.model_name,
                        model_version=worker.model_version,
                        model_sha256=model.sha256,
                    )
                    for item in raw
                ]
                frame_sequence += 1
                counters["detections_seen"] += len(batch)
                response = ingestion.submit(batch)
                counters["detections_created"] += int(response.get("created", 0))
                counters["last_ingestion_at"] = utcnow().isoformat()
                next_sample = monotonic() + live.sample_seconds
                write_health(live.health_path, _health(counters, status="online"))

        except (RuntimeError, IngestionError, ValueError) as exc:
            counters["consecutive_failures"] += 1
            counters["failure"] = str(exc)
        finally:
            if capture is not None:
                capture.release()

        if stop_event.is_set() or reached_limit():
            break

        counters["reconnects"] += 1
        if token_refresh and connected:
            delay = 0.0
            reason = "Refreshing short-lived MediaMTX token."
        else:
            delay = reconnect_delay
            reason = counters["failure"] or "Stream disconnected."
            reconnect_delay = min(
                reconnect_delay * 2, live.reconnect_max_seconds
            )
        write_health(
            live.health_path,
            _health(
                counters,
                status="reconnecting",
                reconnect_in_seconds=delay,
                failure=reason,
            ),
        )
        stop_event.wait(delay)

    final = _health(
        counters,
        status="stopped",
        stopped_at=utcnow().isoformat(),
        uptime_seconds=round(monotonic() - started_mono, 3),
    )
    write_health(live.health_path, final)
    return final
