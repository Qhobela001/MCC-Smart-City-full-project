from __future__ import annotations

import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcc_ai_worker.config import LiveConfig, WorkerConfig
from mcc_ai_worker.live import (
    StreamSession,
    authenticated_rtsp_url,
    run_live_observer,
)
from mcc_ai_worker.model import EXPECTED_CLASSES, sha256_file
from mcc_ai_worker.payloads import build_detection, stable_detection_uuid
from mcc_ai_worker.runner import run_source


class FakeModel:
    sha256 = "model-sha"

    def predict(self, frame, confidence, image_size):
        return [{
            "class_id": 1,
            "class_name": "trash",
            "confidence": 0.91,
            "bbox": {"x1": 10.0, "y1": 20.0, "x2": 30.0, "y2": 40.0},
        }]


class FakeClient:
    def __init__(self):
        self.batches = []

    def submit(self, detections):
        self.batches.append(detections)
        return {"created": len(detections), "items": []}


class FakeSessions:
    def __init__(self):
        self.calls = 0

    def create(self, camera_identifier):
        self.calls += 1
        return StreamSession(
            gateway_path="mcc-cam-001",
            token="signed token/value",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )


class FakeCapture:
    def __init__(self, opened=True):
        self.opened = opened
        self.released = False

    def isOpened(self):
        return self.opened

    def read(self):
        return True, object()

    def release(self):
        self.released = True


class StepClock:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        self.value += 1.0
        return self.value


class AIWorkerTests(unittest.TestCase):
    def test_verified_class_contract(self):
        self.assertEqual(len(EXPECTED_CLASSES), 10)
        self.assertEqual(EXPECTED_CLASSES[1], "trash")
        self.assertEqual(EXPECTED_CLASSES[9], "waste_skip")

    def test_stable_uuid_is_idempotent(self):
        detection = {"class_name": "trash", "bbox": {"x1": 1}}
        first = stable_detection_uuid(
            source_digest="source", frame_index=7,
            detection=detection, model_sha256="model",
        )
        second = stable_detection_uuid(
            source_digest="source", frame_index=7,
            detection=detection, model_sha256="model",
        )
        self.assertEqual(first, second)

    def test_payload_is_forced_to_test(self):
        item = build_detection(
            detection=FakeModel().predict(None, 0.25, 640)[0],
            source_path=Path("sample.jpg"), source_digest="source-sha",
            source_kind="image", frame_index=0, frame_time_seconds=0,
            detected_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            camera_identifier="MCC-CAM-002", stream_identifier="mcc-cam-002",
            camera_head="main", model_name="mcc_detector_v1",
            model_version="v1", model_sha256="model-sha",
        )
        self.assertTrue(item["is_test"])
        self.assertEqual(item["source_type"], "test")
        self.assertEqual(item["detection_type"], "illegal_dumping")
        self.assertEqual(item["attributes"]["bbox_xyxy"]["x1"], 10.0)

    def test_image_run_submits_normalized_detection_and_health(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "sample.jpg"
            source.write_bytes(b"controlled-test-image")
            health_path = root / "health.json"
            config = WorkerConfig(
                backend_url="http://unused", worker_key="key",
                model_path=root / "model.pt", model_sha256="unused",
                model_name="mcc_detector_v1", model_version="v1",
                confidence=0.25, image_size=640, video_sample_seconds=1,
                request_attempts=1, health_path=health_path,
            )
            client = FakeClient()
            result = run_source(
                config, source, camera_identifier="MCC-CAM-002",
                stream_identifier="mcc-cam-002", camera_head="main",
                model=FakeModel(), client=client,
            )
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["detections_created"], 1)
            self.assertEqual(len(client.batches), 1)
            self.assertTrue(client.batches[0][0]["is_test"])
            self.assertEqual(json.loads(health_path.read_text())["status"], "completed")

    def test_live_url_uses_short_lived_token(self):
        session = FakeSessions().create("MCC-CAM-001")
        url = authenticated_rtsp_url("rtsp://mediamtx:8554", session)
        self.assertEqual(
            url,
            "rtsp://mediamtx:8554/mcc-cam-001?jwt=signed%20token%2Fvalue",
        )

    def test_live_observer_is_test_only_sequential_and_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            health_path = root / "live-health.json"
            worker = WorkerConfig(
                backend_url="http://unused", worker_key="key",
                model_path=root / "model.pt", model_sha256="unused",
                model_name="mcc_detector_v1", model_version="v1",
                confidence=0.25, image_size=640, video_sample_seconds=1,
                request_attempts=1, health_path=root / "file-health.json",
            )
            live = LiveConfig(
                camera_identifier="MCC-CAM-001",
                session_url_template="http://unused/{camera_identifier}",
                rtsp_base_url="rtsp://mediamtx:8554",
                sample_seconds=1,
                reconnect_min_seconds=0.001,
                reconnect_max_seconds=0.001,
                token_refresh_seconds=30,
                health_path=health_path,
            )
            client = FakeClient()
            capture = FakeCapture()
            result = run_live_observer(
                worker,
                live,
                model=FakeModel(),
                ingestion=client,
                sessions=FakeSessions(),
                capture_factory=lambda _: capture,
                stop_event=threading.Event(),
                max_frames_analyzed=2,
                monotonic=StepClock(),
            )
            self.assertEqual(result["status"], "stopped")
            self.assertEqual(result["frames_analyzed"], 2)
            self.assertEqual(result["detections_created"], 2)
            self.assertTrue(capture.released)
            self.assertTrue(all(batch[0]["is_test"] for batch in client.batches))
            self.assertTrue(all(
                batch[0]["attributes"]["observation_mode"]
                for batch in client.batches
            ))
            self.assertEqual(json.loads(health_path.read_text())["status"], "stopped")

    def test_live_observer_reconnects_without_touching_gateway(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worker = WorkerConfig(
                backend_url="http://unused", worker_key="key",
                model_path=root / "model.pt", model_sha256="unused",
                model_name="mcc_detector_v1", model_version="v1",
                confidence=0.25, image_size=640, video_sample_seconds=1,
                request_attempts=1, health_path=root / "file-health.json",
            )
            live = LiveConfig(
                camera_identifier="MCC-CAM-001",
                session_url_template="http://unused/{camera_identifier}",
                rtsp_base_url="rtsp://mediamtx:8554",
                sample_seconds=1,
                reconnect_min_seconds=0.001,
                reconnect_max_seconds=0.001,
                token_refresh_seconds=30,
                health_path=root / "live-health.json",
            )
            captures = [FakeCapture(opened=False), FakeCapture(opened=True)]
            result = run_live_observer(
                worker,
                live,
                model=FakeModel(),
                ingestion=FakeClient(),
                sessions=FakeSessions(),
                capture_factory=lambda _: captures.pop(0),
                max_frames_analyzed=1,
                monotonic=StepClock(),
            )
            self.assertEqual(result["frames_analyzed"], 1)
            self.assertEqual(result["reconnects"], 1)
            self.assertEqual(result["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
