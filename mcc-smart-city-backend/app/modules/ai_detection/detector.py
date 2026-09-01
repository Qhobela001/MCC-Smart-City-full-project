from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np
from ultralytics import YOLO

from .associations import bbox_iou


BACKEND_ROOT = Path(__file__).resolve().parents[3]
MODEL_PATH = BACKEND_ROOT / "model_weights" / "mcc_detector_v1.pt"


class MCCDetector:
    """Central wrapper around the trained MCC YOLOv8 detector."""

    def __init__(self, model_path: Path = MODEL_PATH) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                "MCC YOLO model was not found.\n"
                f"Expected model at:\n{self.model_path}"
            )

        print("=" * 70)
        print("Loading MCC YOLO Detector")
        print("=" * 70)
        print(f"Model: {self.model_path}")

        self.model = YOLO(str(self.model_path))
        self.class_names = self.model.names

        print("MCC YOLO detector loaded successfully.\n")
        print("Classes:")
        for class_id, class_name in self.class_names.items():
            print(f"  {class_id}: {class_name}")
        print("=" * 70)

    def _convert_results(
        self,
        results: list[Any],
        *,
        source_label: str = "primary",
        x_offset: float = 0.0,
        y_offset: float = 0.0,
        allowed_classes: set[str] | None = None,
        minimum_by_class: dict[str, float] | None = None,
        parent_detection_index: int | None = None,
    ) -> list[dict[str, Any]]:
        detections: list[dict[str, Any]] = []
        minimum_by_class = minimum_by_class or {}

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls[0].item())
                class_name = str(self.class_names[class_id])
                confidence_score = float(box.conf[0].item())

                if allowed_classes is not None and class_name not in allowed_classes:
                    continue
                if confidence_score < float(minimum_by_class.get(class_name, 0.0)):
                    continue

                x1, y1, x2, y2 = box.xyxy[0].cpu().tolist()
                x1 += x_offset
                x2 += x_offset
                y1 += y_offset
                y2 += y_offset

                detection: dict[str, Any] = {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": round(confidence_score, 4),
                    "bbox": {
                        "x1": round(x1, 2),
                        "y1": round(y1, 2),
                        "x2": round(x2, 2),
                        "y2": round(y2, 2),
                        "width": round(x2 - x1, 2),
                        "height": round(y2 - y1, 2),
                    },
                    "source": source_label,
                }
                if parent_detection_index is not None:
                    detection["parent_detection_index"] = parent_detection_index

                detections.append(detection)

        return detections

    def detect(
        self,
        source: Any,
        confidence: float = 0.25,
        image_size: int = 640,
        device: str | int | None = None,
    ) -> list[dict[str, Any]]:
        results = self.model.predict(
            source=source,
            conf=confidence,
            imgsz=image_size,
            device=device,
            verbose=False,
        )
        return self._convert_results(results, source_label="primary")

    def _source_to_image(self, source: Any) -> np.ndarray | None:
        if isinstance(source, np.ndarray):
            return source
        if isinstance(source, (str, Path)):
            return cv2.imread(str(source))
        return None

    def detect_with_vehicle_details(
        self,
        source: Any,
        confidence: float = 0.25,
        image_size: int = 640,
        device: str | int | None = None,
        *,
        enhance_vehicle_details: bool = True,
        car_recovery_confidence: float = 0.15,
        smoke_detail_confidence: float = 0.12,
        plate_detail_confidence: float = 0.18,
    ) -> list[dict[str, Any]]:
        """Run normal inference plus targeted vehicle-context recovery.

        Wide CCTV frames can produce a useful plate/smoke detection while the
        complete vehicle itself falls below the general confidence threshold.
        The recovery pass therefore searches only the vehicle-related classes
        (car, vehicle_smoke and license_plate) at lower class-specific thresholds.
        Once a car is available, an enlarged crop around that car is analysed a
        second time for small smoke/plate details. Unrelated classes keep using
        the normal full-frame threshold.
        """

        detections = self.detect(
            source=source,
            confidence=confidence,
            image_size=image_size,
            device=device,
        )
        if not enhance_vehicle_details:
            return detections

        image = self._source_to_image(source)
        if image is None:
            return detections

        height, width = image.shape[:2]

        # Recovery pass: lower the threshold only for vehicle-related classes.
        # This solves the common CCTV case where a small car/smoke/plate is below
        # the global threshold while keeping person/trash/etc. at the normal one.
        recovery_confidence = max(
            0.03,
            min(
                float(car_recovery_confidence),
                float(smoke_detail_confidence),
                float(plate_detail_confidence),
            ),
        )
        # Use a larger inference canvas for the targeted recovery pass.
        # Wide CCTV frames lose small vehicle/smoke/plate detail when reduced to
        # the normal 640px inference size, so vehicle-only recovery is allowed
        # to spend more compute in the Test Lab.
        recovery_image_size = max(
            int(image_size),
            1280 if max(width, height) >= 1000 else 960,
        )
        recovery_results = self.model.predict(
            source=image,
            conf=recovery_confidence,
            imgsz=recovery_image_size,
            device=device,
            classes=[3, 4, 5],
            verbose=False,
        )
        recovery_detections = self._convert_results(
            recovery_results,
            source_label="vehicle_context",
            allowed_classes={"car", "license_plate", "vehicle_smoke"},
            minimum_by_class={
                "car": float(car_recovery_confidence),
                "vehicle_smoke": float(smoke_detail_confidence),
                "license_plate": float(plate_detail_confidence),
            },
        )

        merged = list(detections)
        for candidate in recovery_detections:
            duplicate_index: int | None = None
            for index, existing in enumerate(merged):
                if existing["class_name"] != candidate["class_name"]:
                    continue
                if bbox_iou(existing, candidate) >= 0.45:
                    duplicate_index = index
                    break
            if duplicate_index is None:
                merged.append(candidate)
            elif candidate["confidence"] > merged[duplicate_index]["confidence"]:
                merged[duplicate_index] = candidate

        car_indices = [
            index
            for index, detection in enumerate(merged)
            if detection["class_name"] == "car"
        ]
        if not car_indices:
            return merged

        detail_confidence = max(
            0.03,
            min(float(smoke_detail_confidence), float(plate_detail_confidence)),
        )
        minimum_by_class = {
            "vehicle_smoke": float(smoke_detail_confidence),
            "license_plate": float(plate_detail_confidence),
        }

        detail_detections: list[dict[str, Any]] = []
        for car_index in car_indices:
            car = merged[car_index]
            box = car["bbox"]
            expand_x = float(box["width"]) * 0.45
            expand_y = float(box["height"]) * 0.40

            x1 = max(0, int(float(box["x1"]) - expand_x))
            y1 = max(0, int(float(box["y1"]) - expand_y))
            x2 = min(width, int(float(box["x2"]) + expand_x))
            y2 = min(height, int(float(box["y2"]) + expand_y))
            if x2 <= x1 or y2 <= y1:
                continue

            crop = image[y1:y2, x1:x2]
            if crop.size == 0:
                continue

            detail_image_size = max(int(image_size), 960)
            results = self.model.predict(
                source=crop,
                conf=detail_confidence,
                imgsz=detail_image_size,
                device=device,
                verbose=False,
            )
            detail_detections.extend(
                self._convert_results(
                    results,
                    source_label="vehicle_detail",
                    x_offset=float(x1),
                    y_offset=float(y1),
                    allowed_classes={"vehicle_smoke", "license_plate"},
                    minimum_by_class=minimum_by_class,
                    parent_detection_index=car_index,
                )
            )

        # Merge crop-detail detections with the primary + recovery detections.
        for candidate in detail_detections:
            duplicate_index: int | None = None
            for index, existing in enumerate(merged):
                if existing["class_name"] != candidate["class_name"]:
                    continue
                if bbox_iou(existing, candidate) >= 0.45:
                    duplicate_index = index
                    break

            if duplicate_index is None:
                merged.append(candidate)
            elif candidate["confidence"] > merged[duplicate_index]["confidence"]:
                # Preserve the parent vehicle hint from the targeted pass.
                merged[duplicate_index] = candidate

        return merged

    def get_model_info(self) -> dict[str, Any]:
        classes = {
            int(class_id): class_name
            for class_id, class_name in self.class_names.items()
        }
        return {
            "model_name": self.model_path.name,
            "model_path": str(self.model_path),
            "number_of_classes": len(classes),
            "classes": classes,
        }


detector = MCCDetector()
