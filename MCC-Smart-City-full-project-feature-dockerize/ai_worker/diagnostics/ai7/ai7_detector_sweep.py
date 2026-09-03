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
print("CONFIG_CONFIDENCE:", worker.confidence)
print("IMAGE_SIZE:", worker.image_size)
print("CAMERA:", live.camera_identifier)
print()

# Obtain the same short-lived authenticated stream session
# used by the real observer.
session = sessions.create(live.camera_identifier)

print("GATEWAY_PATH:", session.gateway_path)
print("SESSION_EXPIRES:", session.expires_at.isoformat())
print()

# Do NOT print this URL because it contains the temporary JWT.
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

# Warm up the stream.
for _ in range(20):
    ok, frame = capture.read()

# Capture eight separated real frames.
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

    # Consume some frames between samples.
    for _ in range(8):
        capture.read()

capture.release()

if not frames:
    raise RuntimeError("No diagnostic frames captured")

print()
print("Captured frames:", len(frames))
print()

thresholds = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
]

all_detections = []

# Run the detector at a deliberately low floor.
for index, frame in enumerate(frames, start=1):
    detections = model.predict(
        frame,
        confidence=0.05,
        image_size=worker.image_size,
    )

    for detection in detections:
        item = dict(detection)
        item["sample"] = index
        all_detections.append(item)

print("=== THRESHOLD SWEEP ===")

for threshold in thresholds:
    surviving = [
        detection
        for detection in all_detections
        if float(detection["confidence"]) >= threshold
    ]

    grouped = defaultdict(list)

    for detection in surviving:
        grouped[detection["class_name"]].append(
            float(detection["confidence"])
        )

    print()
    print(f"Threshold >= {threshold:.2f}")

    if not grouped:
        print("  NO DETECTIONS")
        continue

    for class_name in sorted(grouped):
        values = grouped[class_name]

        print(
            f"  {class_name:15s} "
            f"count={len(values):3d} "
            f"max={max(values):.6f}"
        )

print()
print("=== TRASH / BAG DETAILS AT >= 0.05 ===")

targets = [
    detection
    for detection in all_detections
    if detection["class_name"] in {"trash", "bag"}
]

if not targets:
    print(
        "NO trash/bag detections "
        "at confidence >= 0.05"
    )
else:
    targets.sort(
        key=lambda item: float(item["confidence"]),
        reverse=True,
    )

    for item in targets:
        print(
            f"sample={item['sample']} "
            f"class={item['class_name']} "
            f"confidence="
            f"{float(item['confidence']):.6f} "
            f"bbox={item['bbox']}"
        )
