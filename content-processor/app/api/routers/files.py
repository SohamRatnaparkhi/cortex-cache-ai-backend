from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import FileService

router = APIRouter(
    prefix='/api/v1/file',
    tags=["file"],
    responses={404: {"description": "Not found"}},
)


@router.post("/process/pdf")
async def process_pdf(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  pdf, and transcribe."""
    try:
        transcription = FileService.extract_text_from_pdf(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
