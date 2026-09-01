from __future__ import annotations

from typing import Literal, Union

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)

from .schemas import (
    DetectionResponse,
    ModelInfoResponse,
    RawImageDetectionResponse,
    RawVideoDetectionResponse,
    VideoDetectionResponse,
)
from .service import ai_detection_service


router = APIRouter(
    prefix="/ai-detection",
    tags=["AI Detection"],
)


# ===========================================================================
# MODEL INFORMATION
# ===========================================================================


@router.get(
    "/model",
    response_model=ModelInfoResponse,
)
def get_model_information():
    """
    Return information about the currently loaded MCC YOLO model.
    """

    return ai_detection_service.model_info()


# ===========================================================================
# IMAGE TEST
# ===========================================================================


@router.post(
    "/detect",
    response_model=Union[
        RawImageDetectionResponse,
        DetectionResponse,
    ],
    status_code=status.HTTP_200_OK,
)
async def detect_image(
    file: UploadFile = File(...),

    # -----------------------------------------------------------------------
    # TEST MODE
    # -----------------------------------------------------------------------
    #
    # raw
    #   Direct mcc_detector_v1.pt inference only.
    #
    # pipeline
    #   Enhanced inference + associations + rules.
    #
    mode: Literal[
        "raw",
        "pipeline",
    ] = Query(
        default="raw",
        description=(
            "raw = test the YOLO model itself; "
            "pipeline = test enhanced inference and rule logic."
        ),
    ),

    # -----------------------------------------------------------------------
    # GENERAL YOLO SETTINGS
    # -----------------------------------------------------------------------

    confidence: float = Query(
        default=0.25,
        ge=0.01,
        le=1.0,
        description=(
            "Minimum YOLO confidence threshold."
        ),
    ),

    image_size: int = Query(
        default=640,
        ge=320,
        le=1920,
        description=(
            "YOLO inference image size. "
            "Used directly during RAW MODEL testing."
        ),
    ),

    # -----------------------------------------------------------------------
    # PIPELINE-ONLY VEHICLE ENHANCEMENT SETTINGS
    # -----------------------------------------------------------------------

    enhance_vehicle_details: bool = Query(
        default=True,
        description=(
            "Pipeline mode only. Enables targeted "
            "car/smoke/plate recovery."
        ),
    ),

    car_recovery_confidence: float = Query(
        default=0.15,
        ge=0.01,
        le=1.0,
    ),

    smoke_detail_confidence: float = Query(
        default=0.12,
        ge=0.01,
        le=1.0,
    ),

    plate_detail_confidence: float = Query(
        default=0.18,
        ge=0.01,
        le=1.0,
    ),
):
    try:
        # ==================================================================
        # RAW MODEL TEST
        # ==================================================================

        if mode == "raw":
            return await ai_detection_service.detect_uploaded_image_raw(
                file=file,
                confidence=confidence,
                image_size=image_size,
            )

        # ==================================================================
        # FULL PIPELINE TEST
        # ==================================================================

        return await ai_detection_service.detect_uploaded_image(
            file=file,
            confidence=confidence,
            enhance_vehicle_details=enhance_vehicle_details,
            car_recovery_confidence=car_recovery_confidence,
            smoke_detail_confidence=smoke_detail_confidence,
            plate_detail_confidence=plate_detail_confidence,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI image detection failed: {exc}",
        ) from exc


# ===========================================================================
# VIDEO TEST
# ===========================================================================


@router.post(
    "/detect-video",
    response_model=Union[
        RawVideoDetectionResponse,
        VideoDetectionResponse,
    ],
    status_code=status.HTTP_200_OK,
)
async def detect_video(
    file: UploadFile = File(...),

    # -----------------------------------------------------------------------
    # TEST MODE
    # -----------------------------------------------------------------------

    mode: Literal[
        "raw",
        "pipeline",
    ] = Query(
        default="raw",
        description=(
            "raw = direct YOLO video evaluation; "
            "pipeline = enhanced tracking/rule evaluation."
        ),
    ),

    # -----------------------------------------------------------------------
    # GENERAL YOLO SETTINGS
    # -----------------------------------------------------------------------

    confidence: float = Query(
        default=0.25,
        ge=0.01,
        le=1.0,
    ),

    image_size: int = Query(
        default=640,
        ge=320,
        le=1920,
        description=(
            "YOLO inference size used in raw model mode."
        ),
    ),

    frame_stride: int = Query(
        default=2,
        ge=1,
        le=30,
        description=(
            "Analyse every Nth source frame. "
            "1 = every frame."
        ),
    ),

    max_sampled_frames: int = Query(
        default=5000,
        ge=30,
        le=20000,
        description=(
            "Maximum number of video samples. "
            "If necessary, effective stride increases "
            "so the whole video is still covered."
        ),
    ),

    # -----------------------------------------------------------------------
    # PIPELINE-ONLY VEHICLE SETTINGS
    # -----------------------------------------------------------------------

    enhance_vehicle_details: bool = Query(
        default=True,
    ),

    car_recovery_confidence: float = Query(
        default=0.15,
        ge=0.01,
        le=1.0,
    ),

    smoke_detail_confidence: float = Query(
        default=0.12,
        ge=0.01,
        le=1.0,
    ),

    plate_detail_confidence: float = Query(
        default=0.18,
        ge=0.01,
        le=1.0,
    ),

    # -----------------------------------------------------------------------
    # PIPELINE-ONLY TEMPORAL SMOKE SETTINGS
    # -----------------------------------------------------------------------

    smoke_window_seconds: float = Query(
        default=3.0,
        ge=0.5,
        le=10.0,
    ),

    smoke_candidate_hits: int = Query(
        default=2,
        ge=2,
        le=20,
    ),

    smoke_strong_hits: int = Query(
        default=3,
        ge=3,
        le=30,
    ),
):
    try:
        # ==================================================================
        # RAW MODEL VIDEO TEST
        # ==================================================================

        if mode == "raw":
            return await ai_detection_service.detect_uploaded_video_raw(
                file=file,
                confidence=confidence,
                frame_stride=frame_stride,
                image_size=image_size,
                max_sampled_frames=max_sampled_frames,
            )

        # ==================================================================
        # FULL PIPELINE VIDEO TEST
        # ==================================================================

        return await ai_detection_service.detect_uploaded_video(
            file=file,
            confidence=confidence,
            frame_stride=frame_stride,
            max_sampled_frames=max_sampled_frames,
            enhance_vehicle_details=enhance_vehicle_details,
            car_recovery_confidence=car_recovery_confidence,
            smoke_detail_confidence=smoke_detail_confidence,
            plate_detail_confidence=plate_detail_confidence,
            smoke_window_seconds=smoke_window_seconds,
            smoke_candidate_hits=smoke_candidate_hits,
            smoke_strong_hits=smoke_strong_hits,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI video detection failed: {exc}",
        ) from exc