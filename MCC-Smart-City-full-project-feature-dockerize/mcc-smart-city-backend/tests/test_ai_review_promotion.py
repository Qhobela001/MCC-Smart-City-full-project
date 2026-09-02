import hashlib
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.main import app
from app.modules.ai_detections import service
from app.modules.ai_detections.models import DetectionReviewStatus


class AIReviewPromotionTests(unittest.TestCase):
    def test_review_and_staged_preview_routes_are_registered(self):
        paths = app.openapi()["paths"]
        self.assertIn("/api/v1/ai-detections/{detection_id}/review", paths)
        self.assertIn("/api/v1/ai-detections/{detection_id}/staged-evidence/{kind}", paths)

    def test_test_detection_can_never_be_confirmed(self):
        detection = SimpleNamespace(
            id=55,
            review_status=DetectionReviewStatus.unreviewed,
            is_test=True,
            source_type=SimpleNamespace(value="test"),
            incident_id=None,
            attributes={},
        )
        with patch.object(service.repository, "lock_detection", return_value=detection):
            with self.assertRaises(HTTPException) as raised:
                service.review_detection(
                    SimpleNamespace(), detection,
                    review_status=DetectionReviewStatus.confirmed,
                    notes="Controlled test approval attempt",
                    department_id=None, priority=None,
                    actor=SimpleNamespace(id=1, is_superuser=True),
                )
        self.assertEqual(raised.exception.status_code, 409)

    def test_staged_bundle_requires_hash_and_operational_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event = root / "operational" / "MCC-CAM-002" / "event"
            event.mkdir(parents=True)
            snapshot = event / "snapshot.jpg"
            clip = event / "clip.mp4"
            snapshot.write_bytes(b"snapshot")
            clip.write_bytes(b"clip")
            relative_snapshot = snapshot.relative_to(root).as_posix()
            relative_clip = clip.relative_to(root).as_posix()
            metadata = {
                "is_test": False,
                "event_id": "event",
                "snapshot": {"path": relative_snapshot, "sha256": hashlib.sha256(b"snapshot").hexdigest(), "size_bytes": 8, "mime_type": "image/jpeg"},
                "clip": {"path": relative_clip, "sha256": hashlib.sha256(b"clip").hexdigest(), "size_bytes": 4, "mime_type": "video/mp4"},
            }
            detection = SimpleNamespace(
                snapshot_path=relative_snapshot,
                clip_path=relative_clip,
                attributes={"evidence": metadata},
            )
            with patch.object(service, "AI_EVIDENCE_STAGING_ROOT", root.resolve()):
                manifest, files = service._validated_staged_bundle(detection)
                self.assertEqual(manifest["event_id"], "event")
                self.assertEqual(len(files), 2)
                clip.write_bytes(b"tampered")
                with self.assertRaises(HTTPException) as raised:
                    service._validated_staged_bundle(detection)
                self.assertEqual(raised.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
