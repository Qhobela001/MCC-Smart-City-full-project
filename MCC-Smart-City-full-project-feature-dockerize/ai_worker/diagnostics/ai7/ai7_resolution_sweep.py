import cv2
from collections import defaultdict

from mcc_ai_worker.config import WorkerConfig, LiveConfig
from mcc_ai_worker.model import MCCModel
from mcc_ai_worker.live import (
    LiveSessionClient,
    authenticated_rtsp_url,
    default_capture_factory,
)

worker = WorkerConfig.from_env()
live = LiveConfig.from_env()

model = MCCModel(
    worker.model_path,
    worker.model_sha256,
)

sessions = LiveSessionClient(
    live.session_url_template,
    worker.worker_key,
)

print("MODEL:", worker.model_name)
print("VERSION:", worker.model_version)
print("PRODUCTION_CONFIDENCE:", worker.confidence)
print("PRODUCTION_IMAGE_SIZE:", worker.image_size)
print("CAMERA:", live.camera_identifier)
print()

session = sessions.create(live.camera_identifier)

print("GATEWAY_PATH:", session.gateway_path)
print("SESSION_EXPIRES:", session.expires_at.isoformat())
print()

stream_url = authenticated_rtsp_url(
    live.rtsp_base_url,
    session,
)

capture = default_capture_factory(stream_url)

if not capture.isOpened():
    raise RuntimeError(
        "Authenticated MediaMTX stream could not be opened"
    )

frames = []

# Warm up.
for _ in range(20):
    capture.read()

# Capture eight real frames.
for sample in range(8):
    ok, frame = capture.read()

    if not ok:
        print(
            f"WARNING: sample {sample + 1} "
            "could not be read"
        )
        continue

    frames.append(frame.copy())

    print(
        f"Captured sample {sample + 1}: "
        f"{frame.shape[1]}x{frame.shape[0]}"
    )

    # Save the first frame so the exact diagnostic scene
    # can be inspected later.
    if sample == 0:
        cv2.imwrite(
            "/output/ai7_resolution_sample.jpg",
            frame,
        )

    for _ in range(8):
        capture.read()

capture.release()

if not frames:
    raise RuntimeError("No diagnostic frames captured")

print()
print("Captured frames:", len(frames))
print()

image_sizes = [640, 960, 1280]
confidence = 0.05

for image_size in image_sizes:
    print()
    print("=" * 60)
    print(
        f"IMAGE SIZE {image_size} "
        f"AT CONFIDENCE {confidence:.2f}"
    )
    print("=" * 60)

    detections = []

    for index, frame in enumerate(frames, start=1):
        results = model.predict(
            frame,
            confidence=confidence,
            image_size=image_size,
        )

        for result in results:
            item = dict(result)
            item["sample"] = index
            detections.append(item)

    grouped = defaultdict(list)

    for detection in detections:
        grouped[detection["class_name"]].append(
            float(detection["confidence"])
        )

    print()
    print("ALL CLASSES:")

    if not grouped:
        print("  NO DETECTIONS")
    else:
        for class_name in sorted(grouped):
            values = grouped[class_name]

            print(
                f"  {class_name:15s} "
                f"count={len(values):3d} "
                f"max={max(values):.6f}"
            )

    targets = [
        detection
        for detection in detections
        if detection["class_name"] in {"trash", "bag"}
    ]

    print()
    print("TRASH / BAG:")

    if not targets:
        print(
            f"  NO trash/bag detections "
            f"at imgsz={image_size}"
        )
    else:
        targets.sort(
            key=lambda item: float(item["confidence"]),
            reverse=True,
        )

        for item in targets:
            print(
                f"  sample={item['sample']} "
                f"class={item['class_name']} "
                f"confidence="
                f"{float(item['confidence']):.6f} "
                f"bbox={item['bbox']}"
            )

print()
print("Diagnostic sample saved:")
print("/output/ai7_resolution_sample.jpg")
