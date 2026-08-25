from pathlib import Path
import argparse

from ultralytics import YOLO


# ============================================================
# PROJECT ROOT
# ============================================================

BACKEND_ROOT = Path(
    __file__
).resolve().parents[1]

MODEL_PATH = (
    BACKEND_ROOT
    / "model_weights"
    / "mcc_detector_v1.pt"
)


# ============================================================
# TEST DETECTOR
# ============================================================

def test_detector(
    image_path: Path,
    confidence: float,
):

    print()
    print("=" * 70)
    print("MCC YOLO DETECTOR TEST")
    print("=" * 70)

    print(
        f"Model: {MODEL_PATH}"
    )

    print(
        f"Image: {image_path}"
    )

    print(
        f"Confidence: {confidence}"
    )

    if not MODEL_PATH.exists():

        raise FileNotFoundError(
            "\nModel does not exist:\n"
            f"{MODEL_PATH}"
        )

    if not image_path.exists():

        raise FileNotFoundError(
            "\nTest image does not exist:\n"
            f"{image_path}"
        )

    print()
    print("Loading model...")

    model = YOLO(
        str(MODEL_PATH)
    )

    print(
        "Model loaded successfully."
    )

    print()
    print("Running inference...")

    results = model.predict(
        source=str(image_path),
        conf=confidence,
        imgsz=640,
        save=True,
        project=str(
            BACKEND_ROOT
            / "runs"
            / "test_detection"
        ),
        name="prediction",
        exist_ok=True,
        verbose=False,
    )

    total_detections = 0

    print()
    print("=" * 70)
    print("DETECTIONS")
    print("=" * 70)

    for result in results:

        if result.boxes is None:
            continue

        for index, box in enumerate(
            result.boxes,
            start=1,
        ):

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

            class_name = (
                model.names[
                    class_id
                ]
            )

            total_detections += 1

            print()
            print(
                f"Detection "
                f"{index}"
            )

            print(
                f"  Class ID: "
                f"{class_id}"
            )

            print(
                f"  Class: "
                f"{class_name}"
            )

            print(
                f"  Confidence: "
                f"{confidence_score:.4f}"
            )

            print(
                "  Bounding box:"
            )

            print(
                f"    x1={x1:.2f}"
            )

            print(
                f"    y1={y1:.2f}"
            )

            print(
                f"    x2={x2:.2f}"
            )

            print(
                f"    y2={y2:.2f}"
            )

    print()
    print("=" * 70)

    print(
        f"Total detections: "
        f"{total_detections}"
    )

    output_directory = (
        BACKEND_ROOT
        / "runs"
        / "test_detection"
        / "prediction"
    )

    print()
    print(
        "Annotated image saved to:"
    )

    print(
        output_directory
    )

    print("=" * 70)


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Test the trained MCC "
            "YOLO detector."
        )
    )

    parser.add_argument(
        "image",
        type=str,
        help=(
            "Path to the test image."
        ),
    )

    parser.add_argument(
        "--confidence",
        type=float,
        default=0.25,
        help=(
            "Detection confidence "
            "threshold."
        ),
    )

    args = parser.parse_args()

    test_detector(
        image_path=Path(
            args.image
        ),
        confidence=args.confidence,
    )


if __name__ == "__main__":
    main()