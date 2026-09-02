from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcc_ai_worker.qualification import EventQualifier


def detection(class_name: str, confidence: float = 0.9, offset: float = 0) -> dict:
    return {
        "class_id": 1,
        "class_name": class_name,
        "confidence": confidence,
        "bbox": {
            "x1": 100 + offset,
            "y1": 100,
            "x2": 160 + offset,
            "y2": 180,
        },
    }


class EventQualificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.audit = Path(self.directory.name) / "qualification.jsonl"
        self.qualifier = EventQualifier(self.audit)
        self.start = datetime(2026, 9, 2, tzinfo=timezone.utc)

    def tearDown(self):
        self.directory.cleanup()

    def observe(self, items: list[dict], frame: int):
        return self.qualifier.observe(
            items, self.start + timedelta(seconds=frame * 2), frame
        )

    def test_single_low_confidence_detection_is_rejected(self):
        qualified, decisions = self.observe([detection("trash", 0.2)], 0)
        self.assertEqual(qualified, [])
        self.assertEqual(decisions[0]["reason"], "below_confidence")

    def test_context_only_detection_is_audited_as_ignored(self):
        qualified, decisions = self.observe([detection("person")], 0)
        self.assertEqual(qualified, [])
        self.assertEqual(decisions[0]["decision"], "ignored")
        self.assertEqual(decisions[0]["reason"], "context_only")
        record = json.loads(self.audit.read_text().strip())
        self.assertEqual(record["class_name"], "person")
        self.assertTrue(record["is_test"])

    def test_illegal_dumping_requires_persistence_and_person_context(self):
        self.observe([detection("trash"), detection("person", offset=30)], 0)
        self.observe([detection("trash", offset=2)], 1)
        qualified, decisions = self.observe([detection("trash", offset=4)], 2)
        self.assertEqual(len(qualified), 1)
        self.assertEqual(
            qualified[0]["qualification"]["event_type"], "illegal_dumping"
        )
        self.assertEqual(qualified[0]["qualification"]["hits"], 3)
        self.assertTrue(qualified[0]["qualification"]["context_found"])
        self.assertEqual(decisions[-1]["decision"], "qualified")

    def test_persistent_trash_without_person_is_not_qualified(self):
        self.observe([detection("trash")], 0)
        self.observe([detection("trash")], 1)
        qualified, decisions = self.observe([detection("trash")], 2)
        self.assertEqual(qualified, [])
        self.assertEqual(decisions[-1]["reason"], "missing_person_context")

    def test_multiple_boxes_in_one_frame_do_not_fake_persistence(self):
        qualified, decisions = self.observe([
            detection("trash", offset=0),
            detection("trash", offset=3),
            detection("trash", offset=6),
            detection("person", offset=20),
        ], 0)
        self.assertEqual(qualified, [])
        candidates = [item for item in decisions if item["class_name"] == "trash"]
        self.assertTrue(all(item["hits"] == 1 for item in candidates))

    def test_vehicle_smoke_requires_nearby_car(self):
        self.observe([detection("vehicle_smoke"), detection("car")], 0)
        self.observe([detection("vehicle_smoke")], 1)
        qualified, _ = self.observe([detection("vehicle_smoke")], 2)
        self.assertEqual(len(qualified), 1)
        self.assertEqual(
            qualified[0]["qualification"]["event_type"],
            "vehicle_smoke_emission",
        )

    def test_audit_trail_is_test_only_and_explains_decisions(self):
        self.observe([detection("pothole")], 0)
        records = [json.loads(line) for line in self.audit.read_text().splitlines()]
        self.assertEqual(records[0]["stage"], "AI-3")
        self.assertTrue(records[0]["is_test"])
        self.assertEqual(records[0]["reason"], "insufficient_persistence")


if __name__ == "__main__":
    unittest.main()
