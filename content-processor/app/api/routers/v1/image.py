from fastapi import APIRouter, HTTPException

from app.schemas.videos import ProcessVideo
from app.services import ImageService

router = APIRouter(
    prefix='/image',
    responses={404: {"description": "Not found in image route"}},
)


@router.post("/process")
async def process_image(request: ProcessVideo.ProcessVideoRequest) -> dict:
    """Process  image, and transcribe."""
    try:
        transcription = ImageService.get_image_transcript(request.video_id)
        return transcription
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
