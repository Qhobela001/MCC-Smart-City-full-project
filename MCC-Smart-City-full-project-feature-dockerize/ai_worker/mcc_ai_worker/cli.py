from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import WorkerConfig
from .runner import run_source


def main() -> None:
    parser = argparse.ArgumentParser(description="MCC Stage AI-1 controlled inference")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--camera-identifier", default="")
    parser.add_argument("--stream-identifier", default="")
    parser.add_argument("--camera-head", choices=("left", "main", "right"), default="main")
    args = parser.parse_args()

    result = run_source(
        WorkerConfig.from_env(),
        args.source,
        camera_identifier=args.camera_identifier,
        stream_identifier=args.stream_identifier,
        camera_head=args.camera_head,
    )
    print(json.dumps(result, indent=2))
