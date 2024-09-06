from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import AudioService

router = APIRouter(
    prefix='/audio',
    responses={404: {"description": "Not found in audio"}},
)


@router.post("/process")
async def process_audio(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  audio, and transcribe."""
    try:
        transcription = AudioService.get_audio_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
