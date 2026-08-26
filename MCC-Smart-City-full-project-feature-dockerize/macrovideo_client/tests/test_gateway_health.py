from __future__ import annotations

from macrovideo.gateway.health import CameraHealthTracker


def test_worker_starts_degraded_then_becomes_offline() -> None:
    tracker = CameraHealthTracker(
        degraded_after_seconds=15,
        offline_after_seconds=60,
    )
    started_at = tracker._started_at

    assert tracker.snapshot(now=started_at + 10).status == "degraded"
    assert tracker.snapshot(now=started_at + 61).status == "offline"


def test_recent_published_frame_is_online_then_ages() -> None:
    tracker = CameraHealthTracker(
        degraded_after_seconds=15,
        offline_after_seconds=60,
    )
    tracker.mark_published()
    last_frame_at = tracker._last_published_at
    assert last_frame_at is not None

    assert tracker.snapshot(now=last_frame_at + 10).status == "online"
    assert tracker.snapshot(now=last_frame_at + 16).status == "degraded"
    assert tracker.snapshot(now=last_frame_at + 61).status == "offline"


def test_stopped_worker_is_immediately_offline() -> None:
    tracker = CameraHealthTracker(
        degraded_after_seconds=15,
        offline_after_seconds=60,
    )
    tracker.mark_published()
    tracker.mark_stopped()

    snapshot = tracker.snapshot()
    assert snapshot.status == "offline"
    assert snapshot.stream_status == "offline"
