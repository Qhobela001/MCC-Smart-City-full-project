from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from .schemas import DetectionResponse, ModelInfoResponse, VideoDetectionResponse
from .service import ai_detection_service

router = APIRouter(prefix="/ai-detection", tags=["AI Detection"])


@router.get("/model", response_model=ModelInfoResponse)
def get_model_information():
    return ai_detection_service.model_info()


@router.post(
    "/detect",
    response_model=DetectionResponse,
    status_code=status.HTTP_200_OK,
)
async def detect_image(
    file: UploadFile = File(...),
    confidence: float = Query(default=0.25, ge=0.01, le=1.0),
):
    try:
        return await ai_detection_service.detect_uploaded_image(file=file, confidence=confidence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI detection failed: {exc}") from exc


@router.post(
    "/detect-video",
    response_model=VideoDetectionResponse,
    status_code=status.HTTP_200_OK,
)
async def detect_video(
    file: UploadFile = File(...),
    confidence: float = Query(default=0.25, ge=0.01, le=1.0),
    frame_stride: int = Query(default=5, ge=1, le=30),
    max_sampled_frames: int = Query(default=1200, ge=30, le=5000),
):
    try:
        return await ai_detection_service.detect_uploaded_video(
            file=file,
            confidence=confidence,
            frame_stride=frame_stride,
            max_sampled_frames=max_sampled_frames,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"AI video detection failed: {exc}") from exc
