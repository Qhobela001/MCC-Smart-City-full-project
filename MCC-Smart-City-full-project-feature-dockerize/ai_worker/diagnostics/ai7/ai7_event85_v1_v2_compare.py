from ultralytics import YOLO

models = {
    "V1": "/models/mcc_detector_v1.pt",
    "V2": "/models/mcc_detector_v2_candidate.pt",
}

image_path = (
    "/evidence/test/MCC-CAM-002/2026/09/03/"
    "9161368a-556d-54db-b392-066938e34ee3/"
    "snapshot.jpg"
)

tests = [
    (640, 0.45, "QUALIFICATION-LEVEL"),
    (640, 0.25, "PRODUCTION"),
    (640, 0.05, "LOW-CONFIDENCE"),
    (1280, 0.05, "HIGH-RES-DIAGNOSTIC"),
]

print("IMAGE:", image_path)

for model_name, model_path in models.items():
    print()
    print("=" * 70)
    print(f"MODEL {model_name}")
    print("=" * 70)

    model = YOLO(model_path)

    print("CLASSES:", model.names)

    for imgsz, conf, label in tests:
        results = model.predict(
            source=image_path,
            imgsz=imgsz,
            conf=conf,
            verbose=False,
        )

        detections = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls.item())
                confidence = float(box.conf.item())
                class_name = str(model.names[class_id])

                xyxy = [
                    round(float(value), 2)
                    for value in box.xyxy[0].tolist()
                ]

                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": xyxy,
                })

        detections.sort(
            key=lambda item: item["confidence"],
            reverse=True,
        )

        print()
        print(
            f"{label}: "
            f"imgsz={imgsz} "
            f"conf={conf}"
        )

        if not detections:
            print("  NO DETECTIONS")
            continue

        for item in detections:
            marker = ""

            if item["class"] in {"trash", "bag"}:
                marker = "  <=== TARGET"

            print(
                f"  {item['class']:15s} "
                f"{item['confidence']:.6f} "
                f"{item['bbox']}"
                f"{marker}"
            )
