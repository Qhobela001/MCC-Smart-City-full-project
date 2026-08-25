from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
from fastapi import UploadFile

from .detector import detector
from .rules import VideoRuleEngine, evaluate_image_rules

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}


class AIDetectionService:
    async def detect_uploaded_image(
        self,
        file: UploadFile,
        confidence: float = 0.25,
    ) -> dict:
        filename = file.filename or "uploaded_image.jpg"
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError("Unsupported image format. Use JPG, JPEG, PNG, BMP or WEBP.")

        temp_path: str | None = None
        try:
            contents = await file.read()
            if not contents:
                raise ValueError("Uploaded image is empty.")

            with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            image = cv2.imread(temp_path)
            if image is None:
                raise ValueError("The uploaded file could not be decoded as an image.")

            height, width = image.shape[:2]
            detections = detector.detect(source=temp_path, confidence=confidence)
            return {
                "filename": filename,
                "image_width": width,
                "image_height": height,
                "detections_count": len(detections),
                "detections": detections,
                "rules": evaluate_image_rules(detections),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def detect_uploaded_video(
        self,
        file: UploadFile,
        confidence: float = 0.25,
        frame_stride: int = 5,
        max_sampled_frames: int = 1200,
    ) -> dict:
        filename = file.filename or "uploaded_video.mp4"
        extension = Path(filename).suffix.lower()
        if extension not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError("Unsupported video format. Use MP4, AVI, MOV, MKV, WEBM or M4V.")

        temp_path: str | None = None
        try:
            contents = await file.read()
            if not contents:
                raise ValueError("Uploaded video is empty.")

            with NamedTemporaryFile(delete=False, suffix=extension) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            capture = cv2.VideoCapture(temp_path)
            if not capture.isOpened():
                raise ValueError("The uploaded file could not be opened as a video.")

            fps = capture.get(cv2.CAP_PROP_FPS) or 0.0
            total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            duration = (total_frames / fps) if fps > 0 else 0.0

            frame_index = 0
            sampled = 0
            stats: dict[str, dict[str, float | int]] = defaultdict(
                lambda: {"detections": 0, "max_confidence": 0.0}
            )
            rule_engine = VideoRuleEngine()

            while sampled < max_sampled_frames:
                ok, frame = capture.read()
                if not ok:
                    break

                if frame_index % frame_stride == 0:
                    detections = detector.detect(source=frame, confidence=confidence)
                    rule_engine.observe(detections)
                    for detection in detections:
                        name = detection["class_name"]
                        stats[name]["detections"] = int(stats[name]["detections"]) + 1
                        stats[name]["max_confidence"] = max(
                            float(stats[name]["max_confidence"]),
                            float(detection["confidence"]),
                        )
                    sampled += 1

                frame_index += 1

            capture.release()

            class_summary = [
                {
                    "class_name": name,
                    "detections": int(values["detections"]),
                    "max_confidence": round(float(values["max_confidence"]), 4),
                }
                for name, values in sorted(stats.items())
            ]

            return {
                "filename": filename,
                "duration_seconds": round(duration, 2),
                "total_frames": total_frames,
                "sampled_frames": sampled,
                "frame_stride": frame_stride,
                "class_summary": class_summary,
                "rules": rule_engine.results(),
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def model_info(self) -> dict:
        info = detector.get_model_info()
        return {
            "model_name": info["model_name"],
            "number_of_classes": info["number_of_classes"],
            "classes": info["classes"],
        }


ai_detection_service = AIDetectionService()
