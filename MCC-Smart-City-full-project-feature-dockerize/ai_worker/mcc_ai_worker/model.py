from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


EXPECTED_CLASSES = {
    0: "person",
    1: "trash",
    2: "bag",
    3: "car",
    4: "license_plate",
    5: "vehicle_smoke",
    6: "pothole",
    7: "road_crack",
    8: "broom",
    9: "waste_skip",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MCCModel:
    def __init__(self, model_path: Path, expected_sha256: str) -> None:
        if not model_path.is_file():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        actual_sha256 = sha256_file(model_path)
        if actual_sha256.lower() != expected_sha256.lower():
            raise ValueError(
                "Model SHA-256 mismatch: "
                f"expected {expected_sha256}, got {actual_sha256}."
            )

        from ultralytics import YOLO

        self._model = YOLO(str(model_path))
        names = {int(key): str(value) for key, value in self._model.names.items()}
        if names != EXPECTED_CLASSES:
            raise ValueError(
                f"Unexpected model classes. Expected {EXPECTED_CLASSES}, got {names}."
            )
        self.sha256 = actual_sha256
        self.names = names

    def predict(self, frame: Any, confidence: float, image_size: int) -> list[dict]:
        results = self._model.predict(
            source=frame,
            conf=confidence,
            imgsz=image_size,
            verbose=False,
        )
        detections: list[dict] = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                x1, y1, x2, y2 = [float(value) for value in box.xyxy[0].cpu().tolist()]
                detections.append(
                    {
                        "class_id": class_id,
                        "class_name": self.names[class_id],
                        "confidence": float(box.conf[0].item()),
                        "bbox": {
                            "x1": round(x1, 2),
                            "y1": round(y1, 2),
                            "x2": round(x2, 2),
                            "y2": round(y2, 2),
                        },
                    }
                )
        return detections
