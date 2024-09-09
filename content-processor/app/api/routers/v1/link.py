from fastapi import APIRouter, HTTPException

from app.schemas import Link
from app.schemas.Common import AgentResponseWrapper
from app.schemas.videos import ProcessVideo
from app.services import LinkService

router = APIRouter(
    prefix='/link',
    responses={404: {"description": "Not found in link route"}},
)


@router.post("/process/git")
async def process_git_link(request: Link.GitLinkRequest) -> AgentResponseWrapper:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_code_from_git_repo(
            request.repo_url, request.metadata)
        print("Got transcription")
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
        "/process/youtube",
        response_model=AgentResponseWrapper,
)
async def process_youtube_link(request: Link.YoutubeLinkRequest) -> AgentResponseWrapper:
    """Process  link, and transcribe."""
    try:
        transcription = LinkService.get_youtube_video_transcript(
            request.video_url, request.metadata)
        return AgentResponseWrapper(
            response=transcription
        )
        # return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
