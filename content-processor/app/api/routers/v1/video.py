from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import VideoService

router = APIRouter(
    prefix='/api/v1/videos',
    responses={404: {"description": "Not found in video route"}},
)


@router.post("/process")
async def process_video(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process video, extract audio, and transcribe."""
    try:
        transcription = VideoService.get_video_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
