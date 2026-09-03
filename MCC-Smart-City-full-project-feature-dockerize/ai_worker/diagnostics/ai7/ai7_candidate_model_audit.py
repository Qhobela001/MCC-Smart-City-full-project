from ultralytics import YOLO

path = "/models/mcc_detector_v2_candidate.pt"

expected = {
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

print("=== CANDIDATE MODEL ===")
print("PATH:", path)

model = YOLO(path)

actual = {
    int(key): str(value)
    for key, value in model.names.items()
}

print("TASK:", model.task)
print("NAMES:", actual)
print()

print("=== MCC COMPATIBILITY ===")

if actual == expected:
    print("PASS: exact MCC class IDs and class names")
else:
    print("FAIL: candidate class mapping differs")
    print()
    print("EXPECTED:")
    print(expected)
    print()
    print("ACTUAL:")
    print(actual)

    print()
    print("DIFFERENCES:")

    all_ids = sorted(set(expected) | set(actual))

    for class_id in all_ids:
        old = expected.get(class_id)
        new = actual.get(class_id)

        if old != new:
            print(
                f"id={class_id} "
                f"expected={old!r} "
                f"actual={new!r}"
            )

print()
print("=== CHECKPOINT PROVENANCE ===")

ckpt = getattr(model, "ckpt", {}) or {}

for key in (
    "date",
    "version",
    "epoch",
    "best_fitness",
):
    print(f"{key}: {ckpt.get(key)!r}")

print()
print("=== TRAIN METRICS ===")

metrics = ckpt.get("train_metrics")

if isinstance(metrics, dict):
    for key in sorted(metrics):
        print(f"{key}: {metrics[key]}")
else:
    print(repr(metrics))

print()
print("=== IMPORTANT TRAIN ARGS ===")

args = ckpt.get("train_args") or {}

important = (
    "model",
    "data",
    "project",
    "name",
    "resume",
    "epochs",
    "batch",
    "imgsz",
    "device",
    "optimizer",
    "lr0",
    "patience",
    "seed",
    "pretrained",
)

for key in important:
    if key in args:
        print(f"{key}: {args[key]}")
