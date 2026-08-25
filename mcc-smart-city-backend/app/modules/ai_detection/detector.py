from pathlib import Path
from typing import Any

from ultralytics import YOLO


# ============================================================
# PROJECT PATHS
# ============================================================

# detector.py:
# backend/app/modules/ai_detection/detector.py
#
# parents[3]:
# backend/
BACKEND_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    BACKEND_ROOT
    / "model_weights"
    / "mcc_detector_v1.pt"
)


# ============================================================
# DETECTOR
# ============================================================

class MCCDetector:
    """
    Central wrapper around the trained MCC YOLOv8 detector.

    The model is loaded once when this module is imported and
    reused for subsequent inference calls.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
    ) -> None:

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

        self.model = YOLO(
            str(self.model_path)
        )

        self.class_names = self.model.names

        print("MCC YOLO detector loaded successfully.")
        print()

        print("Classes:")

        for class_id, class_name in self.class_names.items():
            print(
                f"  {class_id}: {class_name}"
            )

        print("=" * 70)


    # ========================================================
    # DETECT
    # ========================================================

    def detect(
        self,
        source: Any,
        confidence: float = 0.25,
        image_size: int = 640,
        device: str | int | None = None,
    ) -> list[dict]:

        results = self.model.predict(
            source=source,
            conf=confidence,
            imgsz=image_size,
            device=device,
            verbose=False,
        )

        detections: list[dict] = []

        for result in results:

            if result.boxes is None:
                continue

            for box in result.boxes:

                class_id = int(
                    box.cls[0].item()
                )

                confidence_score = float(
                    box.conf[0].item()
                )

                x1, y1, x2, y2 = (
                    box.xyxy[0]
                    .cpu()
                    .tolist()
                )

                width = x2 - x1
                height = y2 - y1

                detection = {
                    "class_id": class_id,
                    "class_name": self.class_names[
                        class_id
                    ],
                    "confidence": round(
                        confidence_score,
                        4,
                    ),
                    "bbox": {
                        "x1": round(x1, 2),
                        "y1": round(y1, 2),
                        "x2": round(x2, 2),
                        "y2": round(y2, 2),
                        "width": round(
                            width,
                            2,
                        ),
                        "height": round(
                            height,
                            2,
                        ),
                    },
                }

                detections.append(
                    detection
                )

        return detections


    # ========================================================
    # MODEL INFORMATION
    # ========================================================

    def get_model_info(self) -> dict:

        classes = {
            int(class_id): class_name
            for class_id, class_name
            in self.class_names.items()
        }

        return {
            "model_name": (
                self.model_path.name
            ),
            "model_path": str(
                self.model_path
            ),
            "number_of_classes": len(
                classes
            ),
            "classes": classes,
        }


# ============================================================
# SINGLETON
#
# Import this object anywhere in the backend rather than
# repeatedly loading the YOLO model.
# ============================================================

detector = MCCDetector()