from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from tempfile import NamedTemporaryFile

import cv2
from fastapi import UploadFile

from .detector import detector
from .rules import VideoRuleEngine, evaluate_image_intelligence


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}


class AIDetectionService:
    # ======================================================================
    # RAW MODEL TESTING
    # ======================================================================
    # These methods intentionally run ONLY detector.detect(...).
    #
    # They do NOT use:
    # - vehicle recovery
    # - secondary vehicle crops
    # - tracking
    # - associations
    # - temporal rules
    # - cleanliness logic
    # - occurrence logic
    #
    # Their purpose is to measure mcc_detector_v1.pt itself.
    # ======================================================================

    async def detect_uploaded_image_raw(
        self,
        file: UploadFile,
        confidence: float = 0.25,
        image_size: int = 640,
    ) -> dict:
        filename = file.filename or "uploaded_image.jpg"
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(
                "Unsupported image format. Use JPG, JPEG, PNG, BMP or WEBP."
            )

        temp_path: str | None = None

        try:
            contents = await file.read()

            if not contents:
                raise ValueError("Uploaded image is empty.")

            with NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            image = cv2.imread(temp_path)

            if image is None:
                raise ValueError(
                    "The uploaded file could not be decoded as an image."
                )

            height, width = image.shape[:2]

            detections = detector.detect(
                source=image,
                confidence=confidence,
                image_size=max(32, int(image_size)),
            )

            return {
                "mode": "raw_model",
                "filename": filename,
                "image_width": width,
                "image_height": height,
                "confidence_threshold": round(float(confidence), 4),
                "image_size": max(32, int(image_size)),
                "detections_count": len(detections),
                "detections": detections,
            }

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    async def detect_uploaded_video_raw(
        self,
        file: UploadFile,
        confidence: float = 0.25,
        frame_stride: int = 2,
        image_size: int = 640,
        max_sampled_frames: int = 5000,
    ) -> dict:
        filename = file.filename or "uploaded_video.mp4"
        extension = Path(filename).suffix.lower()

        if extension not in SUPPORTED_VIDEO_EXTENSIONS:
            raise ValueError(
                "Unsupported video format. Use MP4, AVI, MOV, MKV, WEBM or M4V."
            )

        temp_path: str | None = None
        capture: cv2.VideoCapture | None = None

        try:
            contents = await file.read()

            if not contents:
                raise ValueError("Uploaded video is empty.")

            with NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            capture = cv2.VideoCapture(temp_path)

            if not capture.isOpened():
                raise ValueError(
                    "The uploaded file could not be opened as a video."
                )

            fps = float(
                capture.get(cv2.CAP_PROP_FPS) or 0.0
            )

            total_frames = int(
                capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            )

            video_width = int(
                capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0
            )

            video_height = int(
                capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0
            )

            duration = (
                total_frames / fps
                if fps > 0 and total_frames > 0
                else 0.0
            )

            requested_frame_stride = max(
                1,
                int(frame_stride),
            )

            effective_frame_stride = requested_frame_stride

            # Analyse the WHOLE video.
            #
            # If a video is too long for the configured maximum number
            # of samples, increase the stride evenly instead of stopping
            # before the end of the video.
            if total_frames > 0:
                estimated_samples = (
                    total_frames
                    + requested_frame_stride
                    - 1
                ) // requested_frame_stride

                if (
                    max_sampled_frames > 0
                    and estimated_samples > max_sampled_frames
                ):
                    effective_frame_stride = max(
                        requested_frame_stride,
                        (
                            total_frames
                            + max_sampled_frames
                            - 1
                        )
                        // max_sampled_frames,
                    )

            # Initialise EVERY class in the model.
            #
            # This is important because a class getting zero detections
            # is meaningful when we are deciding whether the model needs
            # retraining.
            raw_stats: dict[
                str,
                dict[str, float | int],
            ] = {}

            for class_id in sorted(detector.class_names):
                class_name = str(
                    detector.class_names[class_id]
                )

                raw_stats[class_name] = {
                    "detections": 0,
                    "frames_detected": 0,
                    "confidence_sum": 0.0,
                    "max_confidence": 0.0,
                }

            frame_index = 0
            sampled = 0
            total_detections = 0
            last_processed_frame_index = -1

            sampled_detections: list[dict] = []

            requested_image_size = max(
                32,
                int(image_size),
            )

            while True:
                ok, frame = capture.read()

                if not ok:
                    break

                if (
                    frame_index
                    % effective_frame_stride
                    == 0
                ):
                    height, width = frame.shape[:2]

                    sample_time_seconds = (
                        frame_index / fps
                        if fps > 0
                        else float(sampled)
                    )

                    # ======================================================
                    # PURE RAW YOLO TEST
                    # ======================================================
                    #
                    # No:
                    # - vehicle recovery
                    # - tracking
                    # - temporal memory
                    # - secondary crop
                    # - rule engine
                    #
                    # This is exactly what mcc_detector_v1.pt returns.
                    # ======================================================

                    detections = detector.detect(
                        source=frame,
                        confidence=confidence,
                        image_size=requested_image_size,
                    )

                    total_detections += len(
                        detections
                    )

                    classes_seen_this_frame: set[
                        str
                    ] = set()

                    for detection in detections:
                        class_name = str(
                            detection["class_name"]
                        )

                        detection_confidence = float(
                            detection["confidence"]
                        )

                        if class_name not in raw_stats:
                            raw_stats[class_name] = {
                                "detections": 0,
                                "frames_detected": 0,
                                "confidence_sum": 0.0,
                                "max_confidence": 0.0,
                            }

                        raw_stats[class_name][
                            "detections"
                        ] = (
                            int(
                                raw_stats[class_name][
                                    "detections"
                                ]
                            )
                            + 1
                        )

                        raw_stats[class_name][
                            "confidence_sum"
                        ] = (
                            float(
                                raw_stats[class_name][
                                    "confidence_sum"
                                ]
                            )
                            + detection_confidence
                        )

                        raw_stats[class_name][
                            "max_confidence"
                        ] = max(
                            float(
                                raw_stats[class_name][
                                    "max_confidence"
                                ]
                            ),
                            detection_confidence,
                        )

                        classes_seen_this_frame.add(
                            class_name
                        )

                    # Count only once per class per frame.
                    #
                    # If one frame contains 5 cars, that is:
                    #
                    # detections += 5
                    # frames_detected += 1
                    #
                    # This lets us distinguish object quantity from
                    # temporal presence.
                    for class_name in classes_seen_this_frame:
                        raw_stats[class_name][
                            "frames_detected"
                        ] = (
                            int(
                                raw_stats[class_name][
                                    "frames_detected"
                                ]
                            )
                            + 1
                        )

                    sampled_detections.append(
                        {
                            "sampled_frame": sampled + 1,
                            "frame_index": frame_index,
                            "time_seconds": round(
                                sample_time_seconds,
                                3,
                            ),
                            "image_width": width,
                            "image_height": height,
                            "detections": detections,
                        }
                    )

                    sampled += 1
                    last_processed_frame_index = (
                        frame_index
                    )

                frame_index += 1

            # ==========================================================
            # BUILD CLASS-BY-CLASS MODEL REPORT
            # ==========================================================

            class_summary: list[dict] = []

            for class_name, values in raw_stats.items():
                detections_count = int(
                    values["detections"]
                )

                frames_detected = int(
                    values["frames_detected"]
                )

                confidence_sum = float(
                    values["confidence_sum"]
                )

                mean_confidence = (
                    confidence_sum
                    / detections_count
                    if detections_count > 0
                    else 0.0
                )

                frame_presence_percent = (
                    (
                        frames_detected
                        / sampled
                    )
                    * 100.0
                    if sampled > 0
                    else 0.0
                )

                class_summary.append(
                    {
                        "class_name": class_name,
                        "detections": detections_count,
                        "frames_detected": frames_detected,
                        "frame_presence_percent": round(
                            frame_presence_percent,
                            2,
                        ),
                        "max_confidence": round(
                            float(
                                values[
                                    "max_confidence"
                                ]
                            ),
                            4,
                        ),
                        "mean_confidence": round(
                            mean_confidence,
                            4,
                        ),
                    }
                )

            if (
                total_frames > 0
                and last_processed_frame_index >= 0
            ):
                analysis_coverage_percent = min(
                    100.0,
                    (
                        (
                            last_processed_frame_index
                            + 1
                        )
                        / total_frames
                    )
                    * 100.0,
                )

            elif sampled > 0:
                analysis_coverage_percent = 100.0

            else:
                analysis_coverage_percent = 0.0

            analysis_end_seconds = (
                last_processed_frame_index / fps
                if (
                    fps > 0
                    and last_processed_frame_index >= 0
                )
                else 0.0
            )

            return {
                "mode": "raw_model",
                "filename": filename,
                "duration_seconds": round(
                    duration,
                    2,
                ),
                "fps": round(
                    fps,
                    3,
                ),
                "video_width": video_width,
                "video_height": video_height,
                "total_frames": total_frames,
                "sampled_frames": sampled,
                "requested_frame_stride": (
                    requested_frame_stride
                ),
                "effective_frame_stride": (
                    effective_frame_stride
                ),
                "analysis_end_seconds": round(
                    analysis_end_seconds,
                    2,
                ),
                "analysis_coverage_percent": round(
                    analysis_coverage_percent,
                    2,
                ),
                "confidence_threshold": round(
                    float(confidence),
                    4,
                ),
                "image_size": requested_image_size,
                "total_detections": total_detections,
                "class_summary": class_summary,
                "sampled_detections": sampled_detections,
            }

        finally:
            if capture is not None:
                capture.release()

            if (
                temp_path
                and os.path.exists(temp_path)
            ):
                os.remove(temp_path)

    # ======================================================================
    # EXISTING ENHANCED / RULE PIPELINE
    # ======================================================================

    async def detect_uploaded_image(
        self,
        file: UploadFile,
        confidence: float = 0.25,
        *,
        enhance_vehicle_details: bool = True,
        car_recovery_confidence: float = 0.15,
        smoke_detail_confidence: float = 0.12,
        plate_detail_confidence: float = 0.18,
    ) -> dict:
        filename = (
            file.filename
            or "uploaded_image.jpg"
        )

        extension = Path(
            filename
        ).suffix.lower()

        if (
            extension
            not in SUPPORTED_IMAGE_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported image format. "
                "Use JPG, JPEG, PNG, BMP or WEBP."
            )

        temp_path: str | None = None

        try:
            contents = await file.read()

            if not contents:
                raise ValueError(
                    "Uploaded image is empty."
                )

            with NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            image = cv2.imread(
                temp_path
            )

            if image is None:
                raise ValueError(
                    "The uploaded file could not "
                    "be decoded as an image."
                )

            height, width = image.shape[:2]

            detections = (
                detector.detect_with_vehicle_details(
                    source=image,
                    confidence=confidence,
                    enhance_vehicle_details=(
                        enhance_vehicle_details
                    ),
                    car_recovery_confidence=(
                        car_recovery_confidence
                    ),
                    smoke_detail_confidence=(
                        smoke_detail_confidence
                    ),
                    plate_detail_confidence=(
                        plate_detail_confidence
                    ),
                )
            )

            intelligence = (
                evaluate_image_intelligence(
                    detections,
                    width,
                    height,
                )
            )

            return {
                "filename": filename,
                "image_width": width,
                "image_height": height,
                "detections_count": len(
                    detections
                ),
                "detections": detections,
                **intelligence,
            }

        finally:
            if (
                temp_path
                and os.path.exists(temp_path)
            ):
                os.remove(temp_path)

    async def detect_uploaded_video(
        self,
        file: UploadFile,
        confidence: float = 0.25,
        frame_stride: int = 5,
        max_sampled_frames: int = 5000,
        *,
        enhance_vehicle_details: bool = True,
        car_recovery_confidence: float = 0.15,
        smoke_detail_confidence: float = 0.12,
        plate_detail_confidence: float = 0.18,
        smoke_window_seconds: float = 3.0,
        smoke_candidate_hits: int = 2,
        smoke_strong_hits: int = 3,
    ) -> dict:
        filename = (
            file.filename
            or "uploaded_video.mp4"
        )

        extension = Path(
            filename
        ).suffix.lower()

        if (
            extension
            not in SUPPORTED_VIDEO_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported video format. "
                "Use MP4, AVI, MOV, MKV, WEBM or M4V."
            )

        temp_path: str | None = None
        capture: cv2.VideoCapture | None = None

        try:
            contents = await file.read()

            if not contents:
                raise ValueError(
                    "Uploaded video is empty."
                )

            with NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temp_file:
                temp_file.write(contents)
                temp_path = temp_file.name

            capture = cv2.VideoCapture(
                temp_path
            )

            if not capture.isOpened():
                raise ValueError(
                    "The uploaded file could not "
                    "be opened as a video."
                )

            fps = (
                capture.get(
                    cv2.CAP_PROP_FPS
                )
                or 0.0
            )

            total_frames = int(
                capture.get(
                    cv2.CAP_PROP_FRAME_COUNT
                )
                or 0
            )

            video_width = int(
                capture.get(
                    cv2.CAP_PROP_FRAME_WIDTH
                )
                or 0
            )

            video_height = int(
                capture.get(
                    cv2.CAP_PROP_FRAME_HEIGHT
                )
                or 0
            )

            duration = (
                total_frames / fps
                if fps > 0
                else 0.0
            )

            requested_frame_stride = max(
                1,
                int(frame_stride),
            )

            estimated_samples = (
                (
                    total_frames
                    + requested_frame_stride
                    - 1
                )
                // requested_frame_stride
                if total_frames > 0
                else 0
            )

            effective_frame_stride = (
                requested_frame_stride
            )

            if (
                max_sampled_frames > 0
                and estimated_samples
                > max_sampled_frames
            ):
                effective_frame_stride = max(
                    requested_frame_stride,
                    (
                        total_frames
                        + max_sampled_frames
                        - 1
                    )
                    // max_sampled_frames,
                )

            frame_index = 0
            sampled = 0
            last_processed_frame_index = -1

            sampled_detections: list[
                dict
            ] = []

            predicted_boxes_count = 0

            stats: dict[
                str,
                dict[str, float | int],
            ] = defaultdict(
                lambda: {
                    "detections": 0,
                    "max_confidence": 0.0,
                }
            )

            rule_engine = VideoRuleEngine(
                smoke_window_seconds=(
                    smoke_window_seconds
                ),
                smoke_candidate_hits=(
                    smoke_candidate_hits
                ),
                smoke_strong_hits=(
                    smoke_strong_hits
                ),
            )

            while True:
                ok, frame = capture.read()

                if not ok:
                    break

                if (
                    frame_index
                    % effective_frame_stride
                    == 0
                ):
                    height, width = (
                        frame.shape[:2]
                    )

                    detections = (
                        detector.detect_with_vehicle_details(
                            source=frame,
                            confidence=confidence,
                            enhance_vehicle_details=(
                                enhance_vehicle_details
                            ),
                            car_recovery_confidence=(
                                car_recovery_confidence
                            ),
                            smoke_detail_confidence=(
                                smoke_detail_confidence
                            ),
                            plate_detail_confidence=(
                                plate_detail_confidence
                            ),
                        )
                    )

                    sample_time_seconds = (
                        frame_index / fps
                        if fps > 0
                        else float(sampled)
                    )

                    tracked_detections = (
                        rule_engine.observe(
                            detections,
                            width,
                            height,
                            time_seconds=(
                                sample_time_seconds
                            ),
                        )
                    )

                    sampled_detections.append(
                        {
                            "sampled_frame": (
                                sampled + 1
                            ),
                            "frame_index": (
                                frame_index
                            ),
                            "time_seconds": round(
                                sample_time_seconds,
                                3,
                            ),
                            "image_width": width,
                            "image_height": height,
                            "detections": (
                                tracked_detections
                            ),
                        }
                    )

                    for detection in (
                        tracked_detections
                    ):
                        if bool(
                            detection.get(
                                "is_predicted"
                            )
                        ):
                            predicted_boxes_count += 1
                            continue

                        name = detection[
                            "class_name"
                        ]

                        stats[name][
                            "detections"
                        ] = (
                            int(
                                stats[name][
                                    "detections"
                                ]
                            )
                            + 1
                        )

                        stats[name][
                            "max_confidence"
                        ] = max(
                            float(
                                stats[name][
                                    "max_confidence"
                                ]
                            ),
                            float(
                                detection[
                                    "confidence"
                                ]
                            ),
                        )

                    sampled += 1
                    last_processed_frame_index = (
                        frame_index
                    )

                frame_index += 1

            intelligence = (
                rule_engine.results()
            )

            class_summary = [
                {
                    "class_name": name,
                    "detections": int(
                        values[
                            "detections"
                        ]
                    ),
                    "max_confidence": round(
                        float(
                            values[
                                "max_confidence"
                            ]
                        ),
                        4,
                    ),
                }
                for name, values in sorted(
                    stats.items()
                )
            ]

            return {
                "filename": filename,
                "duration_seconds": round(
                    duration,
                    2,
                ),
                "fps": round(
                    float(fps),
                    3,
                ),
                "video_width": video_width,
                "video_height": video_height,
                "total_frames": total_frames,
                "sampled_frames": sampled,
                "frame_stride": (
                    effective_frame_stride
                ),
                "requested_frame_stride": (
                    requested_frame_stride
                ),
                "effective_frame_stride": (
                    effective_frame_stride
                ),
                "analysis_end_seconds": round(
                    (
                        last_processed_frame_index
                        / fps
                    )
                    if (
                        fps > 0
                        and last_processed_frame_index
                        >= 0
                    )
                    else 0.0,
                    2,
                ),
                "analysis_coverage_percent": round(
                    min(
                        100.0,
                        (
                            (
                                last_processed_frame_index
                                + 1
                            )
                            / max(
                                total_frames,
                                1,
                            )
                        )
                        * 100.0,
                    ),
                    2,
                ),
                "sampled_detections": (
                    sampled_detections
                ),
                "predicted_boxes_count": (
                    predicted_boxes_count
                ),
                "class_summary": (
                    class_summary
                ),
                **intelligence,
            }

        finally:
            if capture is not None:
                capture.release()

            if (
                temp_path
                and os.path.exists(temp_path)
            ):
                os.remove(temp_path)

    def model_info(self) -> dict:
        info = detector.get_model_info()

        return {
            "model_name": info[
                "model_name"
            ],
            "number_of_classes": info[
                "number_of_classes"
            ],
            "classes": info["classes"],
        }


ai_detection_service = AIDetectionService()