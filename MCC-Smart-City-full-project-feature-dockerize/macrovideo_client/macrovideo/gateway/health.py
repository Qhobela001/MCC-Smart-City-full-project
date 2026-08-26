from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class CameraHealthSnapshot:
    status: str
    stream_status: str
    phase: str
    seconds_since_last_frame: float | None
    failure_code: str | None
    failure_message: str | None
    failure_at: str | None
    consecutive_failures: int


@dataclass(frozen=True, slots=True)
class WorkerFailure:
    code: str
    message: str


def classify_worker_failure(exc: Exception) -> WorkerFailure:
    """Map internal exceptions to stable messages safe for operators and APIs."""
    if isinstance(exc, PermissionError):
        return WorkerFailure(
            code="authentication_rejected",
            message=(
                "The camera rejected the configured V380 credentials. "
                "Verify the camera username and password."
            ),
        )
    if isinstance(exc, TimeoutError):
        return WorkerFailure(
            code="connection_timeout",
            message=(
                "The camera did not respond before the connection timeout. "
                "The gateway will retry automatically."
            ),
        )
    if exc.__class__.__module__.startswith("av"):
        return WorkerFailure(
            code="video_decode_failed",
            message=(
                "The camera sent video that could not be decoded. "
                "The gateway will start a fresh stream session."
            ),
        )
    if isinstance(exc, RuntimeError):
        return WorkerFailure(
            code="publisher_failed",
            message=(
                "The gateway could not publish this camera stream to MediaMTX. "
                "The publisher will be restarted automatically."
            ),
        )
    if isinstance(exc, ConnectionError):
        return WorkerFailure(
            code="stream_ended",
            message=(
                "The camera live session ended unexpectedly. "
                "The gateway will reconnect automatically."
            ),
        )
    if isinstance(exc, OSError):
        return WorkerFailure(
            code="camera_unreachable",
            message=(
                "The camera network address or V380 port is unreachable. "
                "Check camera power and network connectivity."
            ),
        )
    return WorkerFailure(
        code="worker_failed",
        message=(
            "The camera worker encountered an unexpected error and will retry "
            "automatically."
        ),
    )


class CameraHealthTracker:
    """Thread-safe, read-only view of one camera worker's stream health."""

    def __init__(
        self,
        *,
        degraded_after_seconds: float,
        offline_after_seconds: float,
    ) -> None:
        if degraded_after_seconds <= 0:
            raise ValueError("degraded_after_seconds must be positive.")
        if offline_after_seconds <= degraded_after_seconds:
            raise ValueError(
                "offline_after_seconds must be greater than "
                "degraded_after_seconds."
            )

        self.degraded_after_seconds = degraded_after_seconds
        self.offline_after_seconds = offline_after_seconds
        self._lock = threading.Lock()
        self._started_at = time.monotonic()
        self._last_published_at: float | None = None
        self._phase = "starting"
        self._failure_code: str | None = None
        self._failure_message: str | None = None
        self._failure_at: str | None = None
        self._consecutive_failures = 0

    def mark_connecting(self) -> None:
        with self._lock:
            self._phase = "connecting"

    def mark_published(self) -> None:
        with self._lock:
            self._last_published_at = time.monotonic()
            self._phase = "publishing"
            self._failure_code = None
            self._failure_message = None
            self._failure_at = None
            self._consecutive_failures = 0

    def mark_retrying(self, failure: WorkerFailure) -> None:
        with self._lock:
            self._phase = "retrying"
            self._failure_code = failure.code
            self._failure_message = failure.message
            self._failure_at = datetime.now(timezone.utc).isoformat()
            self._consecutive_failures += 1

    def mark_stopped(self) -> None:
        with self._lock:
            self._phase = "stopped"

    def snapshot(
        self,
        *,
        now: float | None = None,
    ) -> CameraHealthSnapshot:
        observed_at = time.monotonic() if now is None else now

        with self._lock:
            started_at = self._started_at
            last_published_at = self._last_published_at
            phase = self._phase
            failure_code = self._failure_code
            failure_message = self._failure_message
            failure_at = self._failure_at
            consecutive_failures = self._consecutive_failures

        if phase == "stopped":
            return CameraHealthSnapshot(
                status="offline",
                stream_status="offline",
                phase=phase,
                seconds_since_last_frame=(
                    None
                    if last_published_at is None
                    else max(0.0, observed_at - last_published_at)
                ),
                failure_code=failure_code,
                failure_message=failure_message,
                failure_at=failure_at,
                consecutive_failures=consecutive_failures,
            )

        reference = (
            last_published_at
            if last_published_at is not None
            else started_at
        )
        age = max(0.0, observed_at - reference)

        if last_published_at is not None and age <= self.degraded_after_seconds:
            state = "online"
        elif age <= self.offline_after_seconds:
            state = "degraded"
        else:
            state = "offline"

        return CameraHealthSnapshot(
            status=state,
            stream_status=state,
            phase=phase,
            seconds_since_last_frame=(
                None if last_published_at is None else age
            ),
            failure_code=failure_code,
            failure_message=failure_message,
            failure_at=failure_at,
            consecutive_failures=consecutive_failures,
        )
