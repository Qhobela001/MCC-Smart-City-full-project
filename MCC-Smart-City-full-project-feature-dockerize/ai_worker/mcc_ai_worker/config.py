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


@dataclass(frozen=True)
class LiveConfig:
    camera_identifier: str
    session_url_template: str
    rtsp_base_url: str
    sample_seconds: float
    reconnect_min_seconds: float
    reconnect_max_seconds: float
    token_refresh_seconds: float
    health_path: Path
    qualification_enabled: bool = False
    qualification_audit_path: Path = Path("/output/qualification-audit.jsonl")
    qualification_min_hits: int = 3
    qualification_max_gap_seconds: float = 8.0
    qualification_context_window_seconds: float = 10.0
    qualification_cooldown_seconds: float = 60.0
    evidence_enabled: bool = False
    evidence_root: Path = Path("/evidence")
    evidence_pre_seconds: float = 6.0
    evidence_post_seconds: float = 6.0
    evidence_sample_seconds: float = 0.5
    evidence_retention_hours: float = 24.0
    evidence_max_storage_bytes: int = 512 * 1024 * 1024

    @classmethod
    def from_env(cls) -> "LiveConfig":
        camera_identifier = os.getenv("AI_LIVE_CAMERA_IDENTIFIER", "").strip()
        if not camera_identifier:
            raise ValueError("AI_LIVE_CAMERA_IDENTIFIER is required for live mode.")

        sample_seconds = float(os.getenv("AI_LIVE_SAMPLE_SECONDS", "2.0"))
        reconnect_min = float(os.getenv("AI_LIVE_RECONNECT_MIN_SECONDS", "2.0"))
        reconnect_max = float(os.getenv("AI_LIVE_RECONNECT_MAX_SECONDS", "30.0"))
        token_refresh = float(os.getenv("AI_LIVE_TOKEN_REFRESH_SECONDS", "30.0"))
        if sample_seconds <= 0:
            raise ValueError("AI_LIVE_SAMPLE_SECONDS must be greater than zero.")
        if reconnect_min <= 0 or reconnect_max < reconnect_min:
            raise ValueError("AI live reconnect bounds are invalid.")
        if token_refresh < 5:
            raise ValueError("AI_LIVE_TOKEN_REFRESH_SECONDS must be at least 5.")

        min_hits = int(os.getenv("AI_QUALIFICATION_MIN_HITS", "3"))
        max_gap = float(os.getenv("AI_QUALIFICATION_MAX_GAP_SECONDS", "8.0"))
        context_window = float(os.getenv(
            "AI_QUALIFICATION_CONTEXT_WINDOW_SECONDS", "10.0"
        ))
        cooldown = float(os.getenv("AI_QUALIFICATION_COOLDOWN_SECONDS", "60.0"))
        if min_hits < 2:
            raise ValueError("AI_QUALIFICATION_MIN_HITS must be at least 2.")
        if min(max_gap, context_window, cooldown) <= 0:
            raise ValueError("AI qualification time settings must be positive.")

        evidence_pre = float(os.getenv("AI_EVIDENCE_PRE_SECONDS", "6.0"))
        evidence_post = float(os.getenv("AI_EVIDENCE_POST_SECONDS", "6.0"))
        evidence_sample = float(os.getenv("AI_EVIDENCE_SAMPLE_SECONDS", "0.5"))
        evidence_retention = float(os.getenv("AI_EVIDENCE_RETENTION_HOURS", "24.0"))
        evidence_max_mb = int(os.getenv("AI_EVIDENCE_MAX_STORAGE_MB", "512"))
        if min(evidence_pre, evidence_post, evidence_sample, evidence_retention) <= 0:
            raise ValueError("AI evidence timing and retention settings must be positive.")
        if evidence_max_mb < 10:
            raise ValueError("AI_EVIDENCE_MAX_STORAGE_MB must be at least 10.")

        return cls(
            camera_identifier=camera_identifier,
            session_url_template=os.getenv(
                "AI_LIVE_SESSION_URL_TEMPLATE",
                "http://backend:8000/api/v1/live-streams/ai/cameras/"
                "{camera_identifier}/session",
            ).strip(),
            rtsp_base_url=os.getenv(
                "AI_LIVE_RTSP_BASE_URL", "rtsp://mediamtx:8554"
            ).rstrip("/"),
            sample_seconds=sample_seconds,
            reconnect_min_seconds=reconnect_min,
            reconnect_max_seconds=reconnect_max,
            token_refresh_seconds=token_refresh,
            health_path=Path(
                os.getenv("AI_LIVE_HEALTH_PATH", "/output/live-health.json")
            ),
            qualification_enabled=os.getenv(
                "AI_QUALIFICATION_ENABLED", "false"
            ).strip().lower() in {"1", "true", "yes", "on"},
            qualification_audit_path=Path(os.getenv(
                "AI_QUALIFICATION_AUDIT_PATH",
                "/output/qualification-audit.jsonl",
            )),
            qualification_min_hits=min_hits,
            qualification_max_gap_seconds=max_gap,
            qualification_context_window_seconds=context_window,
            qualification_cooldown_seconds=cooldown,
            evidence_enabled=os.getenv(
                "AI_EVIDENCE_ENABLED", "false"
            ).strip().lower() in {"1", "true", "yes", "on"},
            evidence_root=Path(os.getenv("AI_EVIDENCE_ROOT", "/evidence")),
            evidence_pre_seconds=evidence_pre,
            evidence_post_seconds=evidence_post,
            evidence_sample_seconds=evidence_sample,
            evidence_retention_hours=evidence_retention,
            evidence_max_storage_bytes=evidence_max_mb * 1024 * 1024,
        )
