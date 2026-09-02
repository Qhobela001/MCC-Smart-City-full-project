from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class IngestionError(RuntimeError):
    pass


class IngestionClient:
    def __init__(self, url: str, worker_key: str, attempts: int = 3) -> None:
        self.url = url
        self.worker_key = worker_key
        self.attempts = attempts

    def submit(self, detections: list[dict]) -> dict:
        if not detections:
            return {"created": 0, "items": []}
        body = json.dumps({"detections": detections}).encode("utf-8")
        request = urllib.request.Request(
            self.url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-AI-Worker-Key": self.worker_key,
            },
        )
        last_error: Exception | None = None
        for attempt in range(1, self.attempts + 1):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if 400 <= exc.code < 500:
                    raise IngestionError(f"Backend rejected batch ({exc.code}): {detail}") from exc
                last_error = exc
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
            if attempt < self.attempts:
                time.sleep(min(2 ** (attempt - 1), 4))
        raise IngestionError(
            f"Ingestion failed after {self.attempts} attempt(s): {last_error}"
        )
