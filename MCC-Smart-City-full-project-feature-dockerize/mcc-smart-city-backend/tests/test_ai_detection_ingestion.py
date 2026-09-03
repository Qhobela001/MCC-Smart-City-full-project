import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.main import app
from app.modules.ai_detections import machine_auth, repository, service
from app.modules.ai_detections.models import DetectionSource, DetectionType
from app.modules.incident_engine import service as incident_engine_service
from app.modules.users.models import UserStatus


class FakeSession:
    def __init__(self):
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0
        self.refreshed = []

    def add(self, value):
        self.added.append(value)

    def commit(self):
        self.commits += 1

    def flush(self):
        self.flushes += 1

    def rollback(self):
        self.rollbacks += 1

    def refresh(self, value):
        self.refreshed.append(value)


class AIDetectionIngestionTests(unittest.TestCase):
    def test_machine_ingestion_route_is_registered(self):
        self.assertIn(
            "/api/v1/ai-detections/ingest/batch",
            app.openapi()["paths"],
        )

    def test_repository_batch_can_defer_commit(self):
        db = FakeSession()
        payload = SimpleNamespace()

        with (
            patch.object(
                repository,
                "_payload_data_with_gis_snapshot",
                return_value={
                    "detection_type": "illegal_dumping",
                    "class_name": "trash",
                    "confidence": 0.9,
                    "detected_at": "2026-09-01T00:00:00Z",
                    "model_name": "test-model",
                },
            ),
            patch.object(
                repository,
                "AIDetection",
                side_effect=lambda **values: SimpleNamespace(**values),
            ),
        ):
            created = repository.create_detection_batch(
                db,
                [payload],
                commit=False,
            )

        self.assertEqual(len(created), 1)
        self.assertEqual(db.flushes, 1)
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.rollbacks, 0)

    def test_service_batch_commits_detection_and_engine_together(self):
        db = FakeSession()
        actor = SimpleNamespace(id=7)
        item = SimpleNamespace(detection_uuid="event-1")
        detection = SimpleNamespace(detection_uuid="event-1")
        processed = []

        def create_batch(_db, payloads, *, commit):
            self.assertEqual(payloads, [item])
            self.assertFalse(commit)
            return [detection]

        with (
            patch.object(
                service.repository,
                "get_detection_by_uuid",
                return_value=None,
            ),
            patch.object(
                service.repository,
                "create_detection_batch",
                side_effect=create_batch,
            ),
            patch.object(
                service.incident_engine_service,
                "process_detection",
                side_effect=lambda _db, value, *, actor: processed.append(
                    (value, actor)
                ),
            ),
            patch.object(
                service.AIDetectionRead,
                "model_validate",
                side_effect=lambda value: value,
            ),
            patch.object(
                service,
                "AIDetectionBatchResponse",
                side_effect=lambda **values: SimpleNamespace(**values),
            ),
        ):
            result = service.create_detection_batch(
                db,
                SimpleNamespace(detections=[item]),
                actor=actor,
            )

        self.assertEqual(result.created, 1)
        self.assertEqual(processed, [(detection, actor)])
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.refreshed, [detection])

    def test_ai_worker_rejects_missing_configuration(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                machine_auth.require_ai_worker(
                    x_ai_worker_key="anything",
                    db=SimpleNamespace(),
                )

        self.assertEqual(raised.exception.status_code, 503)

    def test_ai_worker_rejects_wrong_key(self):
        with patch.dict(
            os.environ,
            {"AI_WORKER_SHARED_KEY": "correct-key"},
            clear=True,
        ):
            with self.assertRaises(HTTPException) as raised:
                machine_auth.require_ai_worker(
                    x_ai_worker_key="wrong-key",
                    db=SimpleNamespace(),
                )

        self.assertEqual(raised.exception.status_code, 401)

    def test_ai_worker_resolves_active_audit_actor(self):
        actor = SimpleNamespace(
            email="ai-ingest@mcc.org.ls",
            is_active=True,
            status=UserStatus.active,
        )

        class Query:
            def filter(self, _condition):
                return self

            def first(self):
                return actor

        db = SimpleNamespace(query=lambda _model: Query())

        with patch.dict(
            os.environ,
            {
                "AI_WORKER_SHARED_KEY": "correct-key",
                "AI_INGEST_ACTOR_EMAIL": actor.email,
            },
            clear=True,
        ):
            resolved = machine_auth.require_ai_worker(
                x_ai_worker_key="correct-key",
                db=db,
            )

        self.assertIs(resolved, actor)


    def test_production_camera_without_review_contract_is_blocked(self):
        db = FakeSession()
        detection = SimpleNamespace(
            id=91,
            incident_id=None,
            is_test=False,
            source_type=DetectionSource.camera,
            camera_identifier="MCC-CAM-001",
            detection_type=DetectionType.illegal_dumping,
            location_name="Pilot Site",
            attributes={},
        )

        result = incident_engine_service.process_detection(
            db, detection, actor=SimpleNamespace(id=1),
        )

        self.assertEqual(result.decision, "review_contract_incomplete")
        self.assertIsNone(result.incident)
        self.assertEqual(result.alerts_created, 0)
        self.assertEqual(
            detection.attributes["incident_engine"]["decision"],
            "review_contract_incomplete",
        )
        self.assertEqual(db.flushes, 1)

    def test_qualified_production_camera_waits_for_human_review(self):
        db = FakeSession()
        detection = SimpleNamespace(
            id=92,
            incident_id=None,
            is_test=False,
            source_type=DetectionSource.camera,
            camera_identifier="MCC-CAM-001",
            detection_type=DetectionType.illegal_dumping,
            location_name="Pilot Site",
            attributes={
                "qualification": {"decision": "qualified", "hits": 3},
                "evidence": {"event_id": "event-92"},
            },
        )

        with patch.object(
            incident_engine_service.alert_repository,
            "active_superadmins",
            return_value=[],
        ):
            result = incident_engine_service.process_detection(
                db, detection, actor=SimpleNamespace(id=1),
            )

        self.assertEqual(result.decision, "awaiting_human_review")
        self.assertIsNone(result.incident)
        self.assertEqual(result.alerts_created, 0)
        self.assertEqual(
            detection.attributes["incident_engine"]["decision"],
            "awaiting_human_review",
        )
        self.assertEqual(db.flushes, 1)

    def test_test_detection_never_creates_operational_incident(self):
        db = FakeSession()
        detection = SimpleNamespace(
            incident_id=None,
            is_test=True,
            attributes={},
        )

        result = incident_engine_service.process_detection(
            db,
            detection,
            actor=SimpleNamespace(id=1),
        )

        self.assertEqual(result.decision, "skipped_test")
        self.assertIsNone(result.incident)
        self.assertEqual(result.alerts_created, 0)
        self.assertEqual(
            detection.attributes["incident_engine"]["decision"],
            "skipped_test",
        )
        self.assertEqual(db.flushes, 1)
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
