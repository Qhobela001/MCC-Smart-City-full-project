from __future__ import annotations

from macrovideo.gateway.models import GatewayCameraConfig
from macrovideo.gateway.service import CameraGatewayService


def config(identifier: str) -> GatewayCameraConfig:
    return GatewayCameraConfig(
        camera_identifier=identifier,
        gateway_path=identifier.lower(),
        host="192.0.2.1",
        port=8800,
        device_id=1,
        username="admin",
        password="test",
    )


class FakeWorker:
    def __init__(self, worker_config: GatewayCameraConfig) -> None:
        self.config = worker_config
        self.stop_calls = 0
        self.join_calls = 0
        self.alive = True
        self.started = False

    def stop(self) -> None:
        self.stop_calls += 1
        self.alive = False

    def join(self, timeout: float) -> None:
        self.join_calls += 1

    def is_alive(self) -> bool:
        return self.alive

    def start(self) -> None:
        self.started = True


def service_with(*workers: FakeWorker) -> CameraGatewayService:
    service = CameraGatewayService.__new__(CameraGatewayService)
    service.worker_stop_timeout = 12.0
    service.workers = {
        worker.config.camera_identifier: worker for worker in workers
    }
    return service


def test_disabling_one_camera_stops_only_its_worker() -> None:
    first = FakeWorker(config("MCC-CAM-001"))
    second = FakeWorker(config("MCC-CAM-002"))
    service = service_with(first, second)

    service._reconcile([first.config])

    assert first.stop_calls == 0
    assert first.is_alive()
    assert second.stop_calls == 1
    assert second.join_calls == 1
    assert service.workers == {"MCC-CAM-001": first}


def test_shutdown_timeout_prevents_duplicate_worker() -> None:
    worker = FakeWorker(config("MCC-CAM-001"))
    service = service_with(worker)

    # Simulate a resource that has not yet responded to stop/close.
    worker.stop = lambda: setattr(worker, "stop_calls", worker.stop_calls + 1)
    service._reconcile([])

    assert worker.is_alive()
    assert service.workers["MCC-CAM-001"] is worker

