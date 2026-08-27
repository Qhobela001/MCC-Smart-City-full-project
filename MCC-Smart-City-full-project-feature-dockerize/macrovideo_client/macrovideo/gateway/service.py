from __future__ import annotations

import os
import signal
import threading
import time
from datetime import datetime, timezone
from typing import Any

from macrovideo.gateway.control import CameraGatewayControlServer
from macrovideo.gateway.models import GatewayCameraConfig
from macrovideo.gateway.registry import (
    CameraRegistryError,
    CameraStatusReportError,
    MCCCameraRegistry,
    MCCCameraStatusReporter,
)
from macrovideo.gateway.worker import CameraWorker


class CameraGatewayService:
    def __init__(self) -> None:
        self.registry = MCCCameraRegistry()
        self.status_reporter = MCCCameraStatusReporter()
        self.poll_seconds = max(
            3.0,
            float(os.getenv("CAMERA_REGISTRY_POLL_SECONDS", "10")),
        )
        self.worker_stop_timeout = max(
            3.0,
            float(os.getenv("CAMERA_WORKER_STOP_TIMEOUT_SECONDS", "12")),
        )
        self.stop_event = threading.Event()
        self.workers: dict[str, CameraWorker] = {}
        self.started_monotonic = time.monotonic()
        self.started_at = datetime.now(timezone.utc)
        self.registry_connected = False
        self.registered_camera_count = 0
        self.last_registry_sync_at: datetime | None = None
        self.registry_failure_at: datetime | None = None

    def health_snapshot(self) -> dict[str, Any]:
        worker_items = list(self.workers.items())
        worker_snapshots = [
            (identifier, worker, worker.health.snapshot())
            for identifier, worker in worker_items
        ]
        worker_states = [
            snapshot.status
            for _, _, snapshot in worker_snapshots
        ]
        workers_alive = sum(
            1 for _, worker in worker_items if worker.is_alive()
        )
        workers_total = len(worker_items)
        state_counts = {
            state: worker_states.count(state)
            for state in ("online", "degraded", "offline")
        }
        gateway_status = (
            "online"
            if (
                self.registry_connected
                and workers_alive == workers_total
                and workers_total == self.registered_camera_count
            )
            else "degraded"
        )
        failure_code = None
        failure_message = None
        failure_at = None
        if not self.registry_connected:
            failure_code = "registry_unavailable"
            failure_message = (
                "The gateway cannot refresh camera configuration from FastAPI. "
                "Existing workers remain active."
            )
            failure_at = (
                self.registry_failure_at.isoformat()
                if self.registry_failure_at is not None
                else None
            )
        elif workers_total != self.registered_camera_count:
            failure_code = "worker_count_mismatch"
            failure_message = (
                "The number of camera workers does not match the current "
                "camera registry."
            )
        elif workers_alive != workers_total:
            failure_code = "worker_stopped"
            failure_message = (
                "One or more registered camera worker threads have stopped."
            )

        return {
            "available": True,
            "status": gateway_status,
            "started_at": self.started_at.isoformat(),
            "uptime_seconds": max(
                0.0,
                time.monotonic() - self.started_monotonic,
            ),
            "registry_connected": self.registry_connected,
            "registered_cameras": self.registered_camera_count,
            "last_registry_sync_at": (
                self.last_registry_sync_at.isoformat()
                if self.last_registry_sync_at is not None
                else None
            ),
            "poll_seconds": self.poll_seconds,
            "workers_total": workers_total,
            "workers_alive": workers_alive,
            "workers_online": state_counts["online"],
            "workers_degraded": state_counts["degraded"],
            "workers_offline": state_counts["offline"],
            "failure_code": failure_code,
            "failure_message": failure_message,
            "failure_at": failure_at,
            "workers": [
                {
                    "camera_identifier": identifier,
                    "status": snapshot.status,
                    "phase": snapshot.phase,
                    "seconds_since_last_frame": (
                        snapshot.seconds_since_last_frame
                    ),
                    "failure_code": snapshot.failure_code,
                    "failure_message": snapshot.failure_message,
                    "failure_at": snapshot.failure_at,
                    "consecutive_failures": snapshot.consecutive_failures,
                    "retry_seconds": worker.retry_seconds,
                }
                for identifier, worker, snapshot in worker_snapshots
            ],
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _report_worker_health(self) -> None:
        for identifier, worker in list(self.workers.items()):
            snapshot = worker.health.snapshot()
            try:
                self.status_reporter.report(
                    camera_identifier=identifier,
                    status=snapshot.status,
                    stream_status=snapshot.stream_status,
                )
            except CameraStatusReportError as exc:
                # Status reporting is deliberately fail-open: loss of FastAPI
                # must never stop or restart an existing camera worker.
                print(
                    f"[GATEWAY] status warning for {identifier}: {exc}",
                    flush=True,
                )

    def request_stop(self, *_: object) -> None:
        self.stop_event.set()

    def send_ptz(self, camera_identifier: str, direction: str, head: str) -> dict[str, Any]:
        identifier = camera_identifier.strip().upper()
        worker = self.workers.get(identifier)
        if worker is None or not worker.is_alive():
            raise LookupError("Camera worker was not found.")
        worker.send_ptz(direction, head)
        return {
            "success": True,
            "camera_identifier": identifier,
            "direction": direction,
            "head": head,
            "message": f"PTZ {direction} command sent to {head} head.",
        }

    def _stop_worker(
        self,
        identifier: str,
        worker: CameraWorker,
        *,
        reason: str,
    ) -> bool:
        print(
            f"[GATEWAY] stopping worker {identifier} ({reason}).",
            flush=True,
        )
        worker.stop()
        worker.join(timeout=self.worker_stop_timeout)

        if worker.is_alive():
            # Keep the worker registered so reconciliation cannot create a
            # duplicate publisher while the original thread is still exiting.
            print(
                f"[GATEWAY] worker {identifier} shutdown pending; "
                "no replacement worker will be started.",
                flush=True,
            )
            return False

        if self.workers.get(identifier) is worker:
            self.workers.pop(identifier, None)
        print(
            f"[GATEWAY] worker {identifier} shutdown confirmed.",
            flush=True,
        )
        return True

    def _reconcile(
        self,
        desired_items: list[GatewayCameraConfig],
    ) -> None:
        desired = {
            item.camera_identifier: item
            for item in desired_items
            if item.enabled
        }

        for identifier, worker in list(self.workers.items()):
            desired_config = desired.get(identifier)
            if desired_config is None or desired_config != worker.config:
                reason = (
                    "disabled or retired"
                    if desired_config is None
                    else "configuration changed"
                )
                self._stop_worker(identifier, worker, reason=reason)

        for identifier, config in desired.items():
            existing = self.workers.get(identifier)
            if existing is not None and existing.is_alive():
                continue

            worker = CameraWorker(config)
            self.workers[identifier] = worker
            worker.start()

    def run(self) -> int:
        signal.signal(signal.SIGTERM, self.request_stop)
        signal.signal(signal.SIGINT, self.request_stop)

        print(
            "[GATEWAY] MCC persistent camera gateway started.",
            flush=True,
        )

        control_server: CameraGatewayControlServer | None = None
        try:
            try:
                control_server = CameraGatewayControlServer(
                    health_provider=self.health_snapshot,
                    ptz_provider=self.send_ptz,
                )
                control_server.start()
            except (OSError, ValueError) as exc:
                # Streaming must remain available even if the optional control
                # endpoint cannot bind. Camera onboarding tests will return 503
                # through the backend until this is corrected.
                print(f"[GATEWAY] control API warning: {exc}", flush=True)

            while not self.stop_event.is_set():
                try:
                    items = self.registry.fetch()
                    self._reconcile(items)
                    self.registry_connected = True
                    self.registered_camera_count = len(items)
                    self.last_registry_sync_at = datetime.now(timezone.utc)
                    self.registry_failure_at = None
                    print(
                        f"[GATEWAY] registry sync complete: "
                        f"{len(items)} V380 camera(s), "
                        f"{len(self.workers)} worker(s).",
                        flush=True,
                    )
                except CameraRegistryError as exc:
                    self.registry_connected = False
                    self.registry_failure_at = datetime.now(timezone.utc)
                    # Existing workers keep streaming even if FastAPI is
                    # briefly unavailable. Registry failure must not drop video.
                    print(f"[GATEWAY] registry warning: {exc}", flush=True)

                self._report_worker_health()

                self.stop_event.wait(self.poll_seconds)
        finally:
            if control_server is not None:
                control_server.stop()

            print("[GATEWAY] stopping camera workers.", flush=True)
            for worker in self.workers.values():
                worker.stop()
            for worker in self.workers.values():
                worker.join(timeout=8)
            self.workers.clear()

        return 0


def main() -> int:
    return CameraGatewayService().run()


if __name__ == "__main__":
    raise SystemExit(main())
