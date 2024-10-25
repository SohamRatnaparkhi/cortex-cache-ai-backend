from fastapi import APIRouter, HTTPException

from app.schemas.Common import AgentResponseWrapper
from app.schemas.Media import (AudioRequest, FileRequest, ImageRequest,
                               VideoRequest)
from app.schemas.videos import ProcessVideo
from app.services import AudioService, FileService, ImageService, VideoService

router = APIRouter(
    prefix='/file',
    responses={404: {"description": "Not found in file route"}},
)


@router.post("/process/pdf")
async def process_pdf(request: FileRequest) -> AgentResponseWrapper:
    """Process  pdf, and transcribe."""
    try:
        transcription = await FileService.extract_text_from_pdf(request.file_id, request.metadata)
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
async def process_image(request: ImageRequest) -> dict:
    """Process  image, and transcribe."""
    try:
        transcription = ImageService.get_image_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
