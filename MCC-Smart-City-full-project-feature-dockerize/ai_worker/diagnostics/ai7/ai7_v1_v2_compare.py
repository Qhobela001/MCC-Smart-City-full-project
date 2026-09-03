from ultralytics import YOLO

models = {
    "V1": "/models/mcc_detector_v1.pt",
    "V2": "/models/mcc_detector_v2_candidate.pt",
}

images = {
    "FAR": "/output/ai7_fn001_far_scene.jpg",
    "NEAR": "/output/ai7_fn001_near_scene.jpg",
}

tests = [
    (640, 0.25, "PRODUCTION"),
    (640, 0.05, "LOW-CONFIDENCE"),
    (1280, 0.05, "HIGH-RES-DIAGNOSTIC"),
]

for model_name, model_path in models.items():
    print()
    print("=" * 70)
    print(f"MODEL {model_name}")
    print("=" * 70)

    model = YOLO(model_path)

    print("CLASSES:", model.names)

    for image_name, image_path in images.items():
        print()
        print("-" * 70)
        print(f"IMAGE: {image_name}")
        print("-" * 70)

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

                    xyxy = box.xyxy[0].tolist()

                    detections.append({
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": [
                            round(float(v), 2)
                            for v in xyxy
                        ],
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
