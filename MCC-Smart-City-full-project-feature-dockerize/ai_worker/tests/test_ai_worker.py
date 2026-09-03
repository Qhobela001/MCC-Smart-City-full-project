from __future__ import annotations

import json
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcc_ai_worker.config import LiveConfig, WorkerConfig
from mcc_ai_worker.evidence import EvidenceBundle
from mcc_ai_worker.ingestion import IngestionError
from mcc_ai_worker.live import (
    StreamSession,
    authenticated_rtsp_url,
    run_live_observer,
)
from mcc_ai_worker.model import EXPECTED_CLASSES, sha256_file
from mcc_ai_worker.outbox import EvidenceDeliveryOutbox
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


class ContextModel(FakeModel):
    def predict(self, frame, confidence, image_size):
        return super().predict(frame, confidence, image_size) + [{
            "class_id": 0,
            "class_name": "person",
            "confidence": 0.88,
            "bbox": {"x1": 15.0, "y1": 15.0, "x2": 55.0, "y2": 80.0},
        }]


class FakeClient:
    def __init__(self):
        self.batches = []

    def submit(self, detections):
        self.batches.append(detections)
        return {"created": len(detections), "items": []}


class FailingClient:
    def __init__(self):
        self.calls = 0

    def submit(self, detections):
        self.calls += 1
        if detections:
            raise IngestionError("backend unavailable")
        return {"created": 0, "items": []}


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


class FakeEvidenceRecorder:
    def __init__(self, root, camera_identifier, *args, **kwargs):
        self.root = Path(root)
        self.camera_identifier = camera_identifier
        self.is_test = kwargs.get("is_test", True)
        self.namespace = "test" if self.is_test else "operational"
        self.pending = []

    def storage_usage_bytes(self):
        if not self.root.exists():
            return 0
        return sum(path.stat().st_size for path in self.root.rglob("*") if path.is_file())

    def enforce_retention(self, now):
        return None

    def add_frame(self, frame, captured_at):
        return None

    def start(self, detection, frame, captured_at, frame_sequence):
        self.pending.append(SimpleNamespace(
            detection=detection,
            captured_at=captured_at,
            frame_sequence=frame_sequence,
        ))
        return "event-id"

    def complete_ready(self, now, force=False):
        if not force:
            return []
        completed = [
            EvidenceBundle(
                detection=item.detection,
                captured_at=item.captured_at,
                frame_sequence=item.frame_sequence,
                snapshot_path=f"{self.namespace}/{self.camera_identifier}/event/snapshot.jpg",
                clip_path=f"{self.namespace}/{self.camera_identifier}/event/clip.mp4",
                metadata={
                    "stage": "AI-5" if not self.is_test else "AI-4",
                    "is_test": self.is_test,
                    "snapshot": {"size_bytes": 10},
                    "clip": {"size_bytes": 20},
                },
            )
            for item in self.pending
        ]
        self.pending = []
        return completed


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

    def test_live_qualification_ingests_only_persistent_candidate(self):
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
                rtsp_base_url="rtsp://mediamtx:8554", sample_seconds=1,
                reconnect_min_seconds=0.001, reconnect_max_seconds=0.001,
                token_refresh_seconds=30, health_path=root / "live-health.json",
                qualification_enabled=True,
                qualification_audit_path=root / "qualification.jsonl",
            )
            client = FakeClient()
            result = run_live_observer(
                worker, live, model=ContextModel(), ingestion=client,
                sessions=FakeSessions(), capture_factory=lambda _: FakeCapture(),
                max_frames_analyzed=3, monotonic=StepClock(),
            )
            created = [item for batch in client.batches for item in batch]
            self.assertEqual(result["stage"], "AI-3")
            self.assertEqual(result["candidates_qualified"], 1)
            self.assertEqual(result["detections_created"], 1)
            self.assertEqual(len(created), 1)
            self.assertTrue(created[0]["is_test"])
            self.assertEqual(created[0]["attributes"]["stage"], "AI-3")
            self.assertEqual(
                created[0]["attributes"]["qualification"]["decision"],
                "qualified",
            )



    def test_backend_failure_leaves_completed_evidence_in_durable_outbox(self):
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
                rtsp_base_url="rtsp://mediamtx:8554", sample_seconds=1,
                reconnect_min_seconds=0.001, reconnect_max_seconds=0.001,
                token_refresh_seconds=30, health_path=root / "live-health.json",
                qualification_enabled=True,
                qualification_audit_path=root / "qualification.jsonl",
                evidence_enabled=True, evidence_root=root / "evidence",
            )
            with patch("mcc_ai_worker.live.EvidenceRecorder", FakeEvidenceRecorder):
                result = run_live_observer(
                    worker, live, model=ContextModel(), ingestion=FailingClient(),
                    sessions=FakeSessions(), capture_factory=lambda _: FakeCapture(),
                    max_frames_analyzed=3, monotonic=StepClock(),
                )
            outbox = EvidenceDeliveryOutbox(
                root / "evidence", "MCC-CAM-001", is_test=True
            )
            self.assertEqual(result["delivery_failures"], 1)
            self.assertEqual(result["delivery_pending"], 1)
            self.assertEqual(outbox.pending_count(), 1)
            self.assertIn("backend unavailable", result["failure"])

    def test_fully_armed_operational_candidate_is_non_test_and_review_bound(self):
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
                rtsp_base_url="rtsp://mediamtx:8554", sample_seconds=1,
                reconnect_min_seconds=0.001, reconnect_max_seconds=0.001,
                token_refresh_seconds=30, health_path=root / "live-health.json",
                qualification_enabled=True,
                qualification_audit_path=root / "qualification.jsonl",
                evidence_enabled=True, evidence_root=root / "evidence",
                operational_mode=True, operational_armed=True,
            )
            client = FakeClient()
            with patch("mcc_ai_worker.live.EvidenceRecorder", FakeEvidenceRecorder):
                result = run_live_observer(
                    worker, live, model=ContextModel(), ingestion=client,
                    sessions=FakeSessions(), capture_factory=lambda _: FakeCapture(),
                    max_frames_analyzed=3, monotonic=StepClock(),
                )
            created = [item for batch in client.batches for item in batch]
            self.assertEqual(result["stage"], "AI-6")
            self.assertTrue(result["operational_armed"])
            self.assertTrue(result["review_contract_required"])
            self.assertEqual(result["delivery_pending"], 0)
            self.assertEqual(result["delivery_acked"], 1)
            self.assertEqual(len(created), 1)
            self.assertFalse(created[0]["is_test"])
            self.assertEqual(created[0]["source_type"], "camera")
            self.assertTrue(created[0]["snapshot_path"].startswith("operational/"))
            self.assertIn("qualification", created[0]["attributes"])
            self.assertIn("evidence", created[0]["attributes"])

    def test_live_evidence_is_completed_before_candidate_ingestion(self):
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
                rtsp_base_url="rtsp://mediamtx:8554", sample_seconds=1,
                reconnect_min_seconds=0.001, reconnect_max_seconds=0.001,
                token_refresh_seconds=30, health_path=root / "live-health.json",
                qualification_enabled=True,
                qualification_audit_path=root / "qualification.jsonl",
                evidence_enabled=True, evidence_root=root / "evidence",
            )
            client = FakeClient()
            with patch("mcc_ai_worker.live.EvidenceRecorder", FakeEvidenceRecorder):
                result = run_live_observer(
                    worker, live, model=ContextModel(), ingestion=client,
                    sessions=FakeSessions(), capture_factory=lambda _: FakeCapture(),
                    max_frames_analyzed=3, monotonic=StepClock(),
                )
            created = [item for batch in client.batches for item in batch]
            self.assertEqual(result["stage"], "AI-4")
            self.assertEqual(result["evidence_started"], 1)
            self.assertEqual(result["evidence_completed"], 1)
            self.assertEqual(result["evidence_failures"], 0)
            self.assertEqual(result["detections_created"], 1)
            self.assertEqual(created[0]["attributes"]["stage"], "AI-4")
            self.assertIsNotNone(created[0]["snapshot_path"])
            self.assertIsNotNone(created[0]["clip_path"])


if __name__ == "__main__":
    unittest.main()
