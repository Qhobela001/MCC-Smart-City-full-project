from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "/output/live-health.json")
    maximum_age = float(sys.argv[2] if len(sys.argv) > 2 else "30")
    try:
        health = json.loads(path.read_text(encoding="utf-8"))
        last_frame = datetime.fromisoformat(
            str(health["last_frame_at"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        age = (datetime.now(timezone.utc) - last_frame).total_seconds()
        if health.get("status") != "online" or age > maximum_age:
            raise ValueError(f"observer status={health.get('status')}, frame_age={age:.1f}s")
    except Exception as exc:
        print(f"AI live observer unhealthy: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
