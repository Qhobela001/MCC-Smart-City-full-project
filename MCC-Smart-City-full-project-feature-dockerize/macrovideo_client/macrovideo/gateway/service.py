from __future__ import annotations

import os
import signal
import threading
import time

from macrovideo.gateway.models import GatewayCameraConfig
from macrovideo.gateway.registry import (
    CameraRegistryError,
    MCCCameraRegistry,
)
from macrovideo.gateway.worker import CameraWorker


class CameraGatewayService:
    def __init__(self) -> None:
        self.registry = MCCCameraRegistry()
        self.poll_seconds = max(
            3.0,
            float(os.getenv("CAMERA_REGISTRY_POLL_SECONDS", "10")),
        )
        self.stop_event = threading.Event()
        self.workers: dict[str, CameraWorker] = {}

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

        while not self.stop_event.is_set():
            try:
                items = self.registry.fetch()
                self._reconcile(items)
                print(
                    f"[GATEWAY] registry sync complete: "
                    f"{len(items)} V380 camera(s), "
                    f"{len(self.workers)} worker(s).",
                    flush=True,
                )
            except CameraRegistryError as exc:
                # Existing workers keep streaming even if FastAPI is
                # briefly unavailable. Registry failure must not drop video.
                print(f"[GATEWAY] registry warning: {exc}", flush=True)

            self.stop_event.wait(self.poll_seconds)

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
