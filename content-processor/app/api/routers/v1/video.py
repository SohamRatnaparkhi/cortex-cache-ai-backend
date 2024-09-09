from fastapi import APIRouter, HTTPException

from app.schemas.Common import AgentResponseWrapper
from app.schemas.Media import VideoRequest
from app.schemas.videos import ProcessVideo
from app.services import LinkService, VideoService

router = APIRouter(
    prefix='/video',
    responses={404: {"description": "Not found in video route"}},
)


@router.post("/process")
async def process_video(request: VideoRequest) -> AgentResponseWrapper:
    """Process video, extract audio, and transcribe."""
    try:
        transcription = VideoService.get_video_transcript(request.video_id, request.metadata)
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
