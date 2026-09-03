from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mcc_ai_worker.config import LiveConfig, WorkerConfig
from mcc_ai_worker.live import run_live_observer
from mcc_ai_worker.outbox import DeliveryOutboxError, EvidenceDeliveryOutbox


class AI6HardeningTests(unittest.TestCase):
    def test_operational_env_requires_separate_arming_flag(self):
        with patch.dict(os.environ, {
            "AI_LIVE_CAMERA_IDENTIFIER": "MCC-CAM-001",
            "AI_OPERATIONAL_MODE": "true",
            "AI_OPERATIONAL_ARMED": "false",
            "AI_QUALIFICATION_ENABLED": "true",
            "AI_EVIDENCE_ENABLED": "true",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "AI_OPERATIONAL_ARMED"):
                LiveConfig.from_env()

    def test_operational_env_requires_qualification_and_evidence(self):
        base = {
            "AI_LIVE_CAMERA_IDENTIFIER": "MCC-CAM-001",
            "AI_OPERATIONAL_MODE": "true",
            "AI_OPERATIONAL_ARMED": "true",
        }
        with patch.dict(os.environ, {
            **base,
            "AI_QUALIFICATION_ENABLED": "false",
            "AI_EVIDENCE_ENABLED": "true",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "QUALIFICATION"):
                LiveConfig.from_env()
        with patch.dict(os.environ, {
            **base,
            "AI_QUALIFICATION_ENABLED": "true",
            "AI_EVIDENCE_ENABLED": "false",
        }, clear=True):
            with self.assertRaisesRegex(ValueError, "EVIDENCE"):
                LiveConfig.from_env()

    def test_fully_armed_operational_env_is_accepted(self):
        with patch.dict(os.environ, {
            "AI_LIVE_CAMERA_IDENTIFIER": "MCC-CAM-001",
            "AI_OPERATIONAL_MODE": "true",
            "AI_OPERATIONAL_ARMED": "true",
            "AI_QUALIFICATION_ENABLED": "true",
            "AI_EVIDENCE_ENABLED": "true",
        }, clear=True):
            config = LiveConfig.from_env()
        self.assertTrue(config.operational_mode)
        self.assertTrue(config.operational_armed)
        self.assertTrue(config.qualification_enabled)
        self.assertTrue(config.evidence_enabled)

    def test_direct_live_config_cannot_bypass_operational_interlock(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            worker = WorkerConfig(
                backend_url="http://unused", worker_key="key",
                model_path=root / "model.pt", model_sha256="unused",
                model_name="mcc_detector_v1", model_version="v1",
                confidence=0.25, image_size=640, video_sample_seconds=1,
                request_attempts=1, health_path=root / "health.json",
            )
            live = LiveConfig(
                camera_identifier="MCC-CAM-001",
                session_url_template="http://unused/{camera_identifier}",
                rtsp_base_url="rtsp://mediamtx:8554", sample_seconds=1,
                reconnect_min_seconds=1, reconnect_max_seconds=2,
                token_refresh_seconds=30, health_path=root / "live.json",
                qualification_enabled=True, evidence_enabled=True,
                operational_mode=True, operational_armed=False,
            )
            with self.assertRaisesRegex(ValueError, "not armed"):
                run_live_observer(worker, live)

    def test_outbox_survives_restart_until_acknowledged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            event = root / "operational" / "MCC-CAM-001" / "2026" / "09" / "03" / "event"
            event.mkdir(parents=True)
            (event / "snapshot.jpg").write_bytes(b"snapshot")
            payload = {
                "detection_uuid": "11111111-1111-1111-1111-111111111111",
                "snapshot_path": "operational/MCC-CAM-001/2026/09/03/event/snapshot.jpg",
                "clip_path": "operational/MCC-CAM-001/2026/09/03/event/clip.mp4",
            }
            first = EvidenceDeliveryOutbox(root, "MCC-CAM-001", is_test=False)
            sidecar = first.enqueue(payload)
            self.assertTrue(sidecar.is_file())

            restarted = EvidenceDeliveryOutbox(root, "MCC-CAM-001", is_test=False)
            pending = restarted.pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].payload["detection_uuid"], payload["detection_uuid"])
            restarted.acknowledge(pending[0])
            self.assertEqual(restarted.pending_count(), 0)
            self.assertFalse(sidecar.exists())

    def test_outbox_rejects_evidence_path_outside_camera_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outbox = EvidenceDeliveryOutbox(root, "MCC-CAM-001", is_test=False)
            with self.assertRaises(DeliveryOutboxError):
                outbox.enqueue({
                    "detection_uuid": "22222222-2222-2222-2222-222222222222",
                    "snapshot_path": "operational/MCC-CAM-OTHER/event/snapshot.jpg",
                })


if __name__ == "__main__":
    unittest.main()
