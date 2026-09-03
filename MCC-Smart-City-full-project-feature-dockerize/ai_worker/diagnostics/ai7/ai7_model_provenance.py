import json
from pathlib import Path

from ultralytics import YOLO

from mcc_ai_worker.config import WorkerConfig

cfg = WorkerConfig.from_env()

print("=== DEPLOYED MODEL ===")
print("PATH:", cfg.model_path)
print("NAME:", cfg.model_name)
print("VERSION:", cfg.model_version)
print("EXPECTED_SHA256:", cfg.model_sha256)
print()

model = YOLO(str(cfg.model_path))

print("=== YOLO MODEL INFO ===")
print("TASK:", getattr(model, "task", None))
print("NAMES:", getattr(model, "names", None))
print()

print("=== MODEL OVERRIDES ===")
overrides = getattr(model, "overrides", None)

if overrides:
    for key in sorted(overrides):
        value = overrides[key]

        if isinstance(value, (str, int, float, bool)) or value is None:
            print(f"{key}: {value}")
        else:
            print(f"{key}: {repr(value)}")
else:
    print("NO OVERRIDES FOUND")

print()
print("=== INNER MODEL ARGS ===")

inner = getattr(model, "model", None)
args = getattr(inner, "args", None)

if isinstance(args, dict):
    for key in sorted(args):
        value = args[key]

        if isinstance(value, (str, int, float, bool)) or value is None:
            print(f"{key}: {value}")
        else:
            print(f"{key}: {repr(value)}")
else:
    print("NO MODEL ARGS FOUND")

print()
print("=== CHECKPOINT METADATA ===")

checkpoint = getattr(model, "ckpt", None)

if not isinstance(checkpoint, dict):
    print("NO CHECKPOINT DICTIONARY AVAILABLE")
else:
    print("CHECKPOINT KEYS:")
    print(", ".join(sorted(str(key) for key in checkpoint.keys())))
    print()

    interesting_keys = [
        "date",
        "version",
        "license",
        "docs",
        "epoch",
        "best_fitness",
        "train_args",
        "train_metrics",
    ]

    for key in interesting_keys:
        if key not in checkpoint:
            continue

        value = checkpoint[key]

        print(f"--- {key} ---")

        if isinstance(value, dict):
            for subkey in sorted(value):
                subvalue = value[subkey]

                if (
                    isinstance(
                        subvalue,
                        (str, int, float, bool),
                    )
                    or subvalue is None
                ):
                    print(f"{subkey}: {subvalue}")
                else:
                    print(
                        f"{subkey}: "
                        f"{repr(subvalue)[:500]}"
                    )
        else:
            print(repr(value)[:2000])

        print()
