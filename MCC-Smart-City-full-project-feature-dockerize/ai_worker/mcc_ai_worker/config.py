from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


VERIFIED_MODEL_SHA256 = (
    "845026048d3bb44831b069cbc36e189bb0f"
    "c0bbcff4f4445b8fcab382359d9af"
)


@dataclass(frozen=True)
class WorkerConfig:
    backend_url: str
    worker_key: str
    model_path: Path
    model_sha256: str
    model_name: str
    model_version: str
    confidence: float
    image_size: int
    video_sample_seconds: float
    request_attempts: int
    health_path: Path

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        key = os.getenv("AI_WORKER_SHARED_KEY", "").strip()
        if not key:
            raise ValueError("AI_WORKER_SHARED_KEY is required.")

        confidence = float(os.getenv("AI_CONFIDENCE", "0.25"))
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("AI_CONFIDENCE must be between 0 and 1.")

        sample_seconds = float(os.getenv("AI_VIDEO_SAMPLE_SECONDS", "1.0"))
        if sample_seconds <= 0:
            raise ValueError("AI_VIDEO_SAMPLE_SECONDS must be greater than zero.")

        attempts = int(os.getenv("AI_REQUEST_ATTEMPTS", "3"))
        if attempts < 1:
            raise ValueError("AI_REQUEST_ATTEMPTS must be at least 1.")

        return cls(
            backend_url=os.getenv(
                "AI_BACKEND_URL",
                "http://backend:8000/api/v1/ai-detections/ingest/batch",
            ).strip(),
            worker_key=key,
            model_path=Path(os.getenv("AI_MODEL_PATH", "/models/mcc_detector_v1.pt")),
            model_sha256=os.getenv(
                "AI_MODEL_SHA256", VERIFIED_MODEL_SHA256
            ).strip().lower(),
            model_name=os.getenv("AI_MODEL_NAME", "mcc_detector_v1").strip(),
            model_version=os.getenv("AI_MODEL_VERSION", "v1").strip(),
            confidence=confidence,
            image_size=int(os.getenv("AI_IMAGE_SIZE", "640")),
            video_sample_seconds=sample_seconds,
            request_attempts=attempts,
            health_path=Path(os.getenv("AI_HEALTH_PATH", "/output/health.json")),
        )
