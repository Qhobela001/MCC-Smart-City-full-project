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
        self.stop_event = threading.Event()
        self.workers: dict[str, CameraWorker] = {}
        self.started_monotonic = time.monotonic()
        self.started_at = datetime.now(timezone.utc)
        self.registry_connected = False
        self.registered_camera_count = 0
        self.last_registry_sync_at: datetime | None = None

    def health_snapshot(self) -> dict[str, Any]:
        worker_items = list(self.workers.items())
        worker_states = [
            worker.health.snapshot().status
            for _, worker in worker_items
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
                print(
                    f"[GATEWAY] stopping worker {identifier} "
                    f"(removed or configuration changed).",
                    flush=True,
                )
                worker.stop()
                worker.join(timeout=5)
                self.workers.pop(identifier, None)

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
                    print(
                        f"[GATEWAY] registry sync complete: "
                        f"{len(items)} V380 camera(s), "
                        f"{len(self.workers)} worker(s).",
                        flush=True,
                    )
                except CameraRegistryError as exc:
                    self.registry_connected = False
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
