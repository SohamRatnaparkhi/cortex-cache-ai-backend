from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import LinkService, VideoService

router = APIRouter(
    prefix='/api/v1/videos',
    responses={404: {"description": "Not found in video route"}},
)

@router.post("/process/git")
async def process_link(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_code_from_git_repo(request.video_id)
        return transcription
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.post("/process/youtube")
async def process_link(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_youtube_video_transcript(
            request.video_id)
        return transcription
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}")
