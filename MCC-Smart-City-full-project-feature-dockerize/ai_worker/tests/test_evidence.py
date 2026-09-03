from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcc_ai_worker.evidence import (
    EncodedFrame,
    EvidenceCaptureError,
    EvidenceRecorder,
)
from mcc_ai_worker.payloads import build_live_detection


def fake_encode(frame: object, bbox: dict | None) -> bytes:
    marker = b"annotated" if bbox else b"frame"
    return marker + str(frame).encode("utf-8")


def fake_clip(path: Path, samples: list[EncodedFrame], fps: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"|".join(item.jpeg for item in samples) + str(fps).encode())


def qualified_detection() -> dict:
    return {
        "class_id": 1,
        "class_name": "trash",
        "confidence": 0.91,
        "bbox": {"x1": 10, "y1": 20, "x2": 80, "y2": 100},
        "qualification": {
            "event_type": "illegal_dumping",
            "track_id": 7,
            "hits": 3,
            "decision": "qualified",
        },
    }


class EvidenceRecorderTests(unittest.TestCase):
    def test_qualified_candidate_creates_hashed_snapshot_clip_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", pre_seconds=2, post_seconds=2,
                sample_seconds=1, encode_jpeg=fake_encode, write_clip=fake_clip,
            )
            start = datetime(2026, 9, 2, tzinfo=timezone.utc)
            recorder.add_frame("pre-1", start)
            recorder.add_frame("pre-2", start + timedelta(seconds=1))
            recorder.start(
                qualified_detection(), "event", start + timedelta(seconds=2), 4
            )
            recorder.add_frame("post-1", start + timedelta(seconds=3))
            recorder.add_frame("post-2", start + timedelta(seconds=4))
            completed = recorder.complete_ready(start + timedelta(seconds=4))
            self.assertEqual(len(completed), 1)
            item = completed[0]
            snapshot = root / item.snapshot_path
            clip = root / item.clip_path
            manifest = json.loads((snapshot.parent / "manifest.json").read_text())
            self.assertTrue(snapshot.is_file())
            self.assertTrue(clip.is_file())
            self.assertEqual(
                manifest["snapshot"]["sha256"],
                hashlib.sha256(snapshot.read_bytes()).hexdigest(),
            )
            self.assertEqual(
                manifest["clip"]["sha256"],
                hashlib.sha256(clip.read_bytes()).hexdigest(),
            )
            self.assertTrue(manifest["is_test"])
            self.assertFalse(manifest["post_window_truncated"])

    def test_payload_links_test_evidence_without_incident(self):
        item = build_live_detection(
            detection=qualified_detection(),
            captured_at=datetime(2026, 9, 2, tzinfo=timezone.utc),
            camera_identifier="MCC-CAM-002", gateway_path="mcc-cam-002",
            frame_sequence=4, model_name="mcc_detector_v1",
            model_version="v1", model_sha256="sha",
            snapshot_path="test/camera/event/snapshot.jpg",
            clip_path="test/camera/event/clip.mp4",
            evidence_metadata={"stage": "AI-4", "is_test": True},
        )
        self.assertTrue(item["is_test"])
        self.assertEqual(item["attributes"]["stage"], "AI-4")
        self.assertEqual(item["snapshot_path"], "test/camera/event/snapshot.jpg")
        self.assertNotIn("incident_id", item)

    def test_operational_bundle_and_payload_are_explicitly_non_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", pre_seconds=1, post_seconds=1,
                sample_seconds=1, encode_jpeg=fake_encode,
                write_clip=fake_clip, is_test=False,
            )
            start = datetime(2026, 9, 2, tzinfo=timezone.utc)
            recorder.add_frame("pre", start)
            recorder.start(qualified_detection(), "event", start, 1)
            recorder.add_frame("post", start + timedelta(seconds=1))
            bundle = recorder.complete_ready(start + timedelta(seconds=1))[0]
            self.assertTrue(bundle.snapshot_path.startswith("operational/"))
            self.assertFalse(bundle.metadata["is_test"])
            item = build_live_detection(
                detection=bundle.detection, captured_at=bundle.captured_at,
                camera_identifier="MCC-CAM-002", gateway_path="mcc-cam-002",
                frame_sequence=1, model_name="mcc_detector_v1",
                model_version="v1", model_sha256="sha",
                snapshot_path=bundle.snapshot_path, clip_path=bundle.clip_path,
                evidence_metadata=bundle.metadata, is_test=False,
            )
            self.assertFalse(item["is_test"])
            self.assertEqual(item["source_type"], "camera")
            self.assertEqual(item["attributes"]["stage"], "AI-5")

    def test_camera_identifier_cannot_escape_evidence_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(EvidenceCaptureError):
                EvidenceRecorder(Path(directory), "../")

    def test_retention_enforces_storage_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", max_storage_bytes=10,
                encode_jpeg=fake_encode, write_clip=fake_clip,
            )
            first_dir = recorder.scope_root / "date" / "old"
            second_dir = recorder.scope_root / "date" / "new"
            first_dir.mkdir(parents=True, exist_ok=True)
            second_dir.mkdir(parents=True, exist_ok=True)
            (first_dir / "manifest.json").write_bytes(b"{}")
            (first_dir / "clip.mp4").write_bytes(b"a" * 8)
            (second_dir / "manifest.json").write_bytes(b"{}")
            (second_dir / "clip.mp4").write_bytes(b"b" * 8)
            for path in first_dir.iterdir():
                os.utime(path, (1, 1))
            recorder.enforce_retention(datetime.now(timezone.utc))
            remaining = sum(
                path.stat().st_size for path in root.rglob("*") if path.is_file()
            )
            self.assertLessEqual(remaining, 10)



    def test_new_operational_bundle_is_preserved_before_capacity_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", pre_seconds=1, post_seconds=1,
                sample_seconds=1, max_storage_bytes=10, is_test=False,
                encode_jpeg=fake_encode, write_clip=fake_clip,
            )
            start = datetime(2026, 9, 3, tzinfo=timezone.utc)
            recorder.add_frame("pre", start)
            recorder.start(qualified_detection(), "event", start, 1)
            recorder.add_frame("post", start + timedelta(seconds=1))
            bundle = recorder.complete_ready(start + timedelta(seconds=1))[0]
            event_dir = (root / bundle.snapshot_path).parent

            self.assertTrue(event_dir.exists())
            with self.assertRaises(EvidenceCaptureError):
                recorder.enforce_retention(start + timedelta(seconds=1))
            self.assertTrue(event_dir.exists())
            self.assertTrue((event_dir / "snapshot.jpg").exists())
            self.assertTrue((event_dir / "clip.mp4").exists())

    def test_operational_retention_never_deletes_review_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", max_storage_bytes=10,
                encode_jpeg=fake_encode, write_clip=fake_clip, is_test=False,
            )
            event = recorder.scope_root / "date" / "review-pending"
            event.mkdir(parents=True, exist_ok=True)
            (event / "manifest.json").write_bytes(b"{}")
            (event / "clip.mp4").write_bytes(b"x" * 20)
            for path in event.iterdir():
                os.utime(path, (1, 1))

            with self.assertRaises(EvidenceCaptureError):
                recorder.enforce_retention(datetime.now(timezone.utc))

            self.assertTrue(event.exists())
            self.assertTrue((event / "clip.mp4").exists())

    def test_retention_deletes_whole_event_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder = EvidenceRecorder(
                root, "MCC-CAM-002", max_storage_bytes=12,
                encode_jpeg=fake_encode, write_clip=fake_clip,
            )
            old = recorder.scope_root / "date" / "old"
            new = recorder.scope_root / "date" / "new"
            for target, marker in ((old, b"a"), (new, b"b")):
                target.mkdir(parents=True, exist_ok=True)
                (target / "manifest.json").write_bytes(b"{}")
                (target / "snapshot.jpg").write_bytes(marker * 5)
                (target / "clip.mp4").write_bytes(marker * 5)
            for path in old.iterdir():
                os.utime(path, (1, 1))
            recorder.enforce_retention(datetime.now(timezone.utc))
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())


if __name__ == "__main__":
    unittest.main()
