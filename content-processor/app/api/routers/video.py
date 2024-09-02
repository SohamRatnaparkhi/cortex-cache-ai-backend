import os

from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import VideoService
from app.utils.AV import (extract_audio_from_video,
                          process_audio_for_transcription)
from app.utils.s3 import S3Operations

router = APIRouter(
    prefix='/api/v1/videos',
    tags=["videos"],
    responses={404: {"description": "Not found"}},
)


@router.post("/process")
async def process_video(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process video, extract audio, and transcribe."""
    try:
        transcription = VideoService.get_video_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
