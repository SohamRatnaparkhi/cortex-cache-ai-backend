from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import LinkService

router = APIRouter(
    prefix='/link',
    responses={404: {"description": "Not found in link route"}},
)


@router.post("/process/git")
async def process_link(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_code_from_git_repo(
            request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/youtube")
async def process_link(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_youtube_video_transcript(
            request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
