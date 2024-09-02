import os

from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import AudioService
from app.utils.s3 import S3Operations

router = APIRouter(
    prefix='/api/v1/audio',
    tags=["audio"],
    responses={404: {"description": "Not found"}},
)


@router.post("/process")
async def process_audio(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  audio, and transcribe."""
    try:
        transcription = AudioService.get_audio_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
