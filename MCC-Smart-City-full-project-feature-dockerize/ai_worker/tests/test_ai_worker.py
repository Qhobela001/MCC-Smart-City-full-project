from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from mcc_ai_worker.config import WorkerConfig
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


if __name__ == "__main__":
    unittest.main()
