from __future__ import annotations

import argparse
import json
import signal
import threading
from dataclasses import replace
from pathlib import Path

from .config import LiveConfig, WorkerConfig
from .live import run_live_observer
from .runner import run_source


def main() -> None:
    parser = argparse.ArgumentParser(description="MCC isolated AI inference worker")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--camera-identifier", default="")
    parser.add_argument("--stream-identifier", default="")
    parser.add_argument(
        "--camera-head",
        choices=("left", "main", "right", "composite"),
        default="main",
    )
    parser.add_argument("--max-runtime-seconds", type=float)
    args = parser.parse_args()

    worker = WorkerConfig.from_env()
    if args.live:
        live = LiveConfig.from_env()
        if args.camera_identifier:
            live = replace(live, camera_identifier=args.camera_identifier)
        stop_event = threading.Event()
        signal.signal(signal.SIGTERM, lambda *_: stop_event.set())
        signal.signal(signal.SIGINT, lambda *_: stop_event.set())
        result = run_live_observer(
            worker,
            live,
            stop_event=stop_event,
            max_runtime_seconds=args.max_runtime_seconds,
        )
    else:
        if args.source is None:
            parser.error("--source is required unless --live is selected.")
        result = run_source(
            worker,
            args.source,
            camera_identifier=args.camera_identifier,
            stream_identifier=args.stream_identifier,
            camera_head=args.camera_head,
        )
    print(json.dumps(result, indent=2))
