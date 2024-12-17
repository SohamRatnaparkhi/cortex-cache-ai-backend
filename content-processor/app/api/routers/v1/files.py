import time
import uuid

from fastapi import APIRouter, HTTPException

from app.schemas.Common import AgentResponseWrapper
from app.schemas.Media import (AudioRequest, FileRequest, ImageRequest,
                               VideoRequest)
from app.services import AudioService, FileService, ImageService, VideoService
from app.utils.app_logger_config import logger

router = APIRouter(
    prefix='/file',
    responses={404: {"description": "Not found in file route"}},
)


@router.post("/process/pdf")
async def process_pdf(request: FileRequest) -> AgentResponseWrapper:
    """Process  pdf, and transcribe."""
    try:
        req_id = str(uuid.uuid4())
        logger.info(f"Processing PDF with request id: {req_id}")
        start_time = time.time()
        transcription = await FileService.extract_text_from_pdf(request.file_id, request.metadata)
        logger.info(
            f"Request {req_id}  processed in {time.time() - start_time} seconds")
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/audio")
async def process_audio(request: AudioRequest) -> dict:
    """Process  audio, and transcribe."""
    try:
        transcription = await AudioService.get_audio_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/video")
async def process_video(request: VideoRequest) -> AgentResponseWrapper:
    """Process video, extract audio, and transcribe."""
    try:
        transcription = await VideoService.get_video_transcript(request.video_id, request.metadata)
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/image")
async def process_image(request: ImageRequest) -> AgentResponseWrapper:
    """Process  image, and transcribe."""
    try:
        transcription = await ImageService.get_image_transcript(
            request.image_id, request.metadata)
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
