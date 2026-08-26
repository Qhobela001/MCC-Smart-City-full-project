from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CameraHealthSnapshot:
    status: str
    stream_status: str
    phase: str
    seconds_since_last_frame: float | None


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

    def mark_connecting(self) -> None:
        with self._lock:
            self._phase = "connecting"

    def mark_published(self) -> None:
        with self._lock:
            self._last_published_at = time.monotonic()
            self._phase = "publishing"

    def mark_retrying(self) -> None:
        with self._lock:
            self._phase = "retrying"

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
        )
