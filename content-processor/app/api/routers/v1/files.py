from fastapi import APIRouter, HTTPException

from app.schemas.Common import AgentResponseWrapper
from app.schemas.Media import FileRequest
from app.services import FileService

router = APIRouter(
    prefix='/file',
    responses={404: {"description": "Not found in file route"}},
)


@router.post("/process/pdf")
async def process_pdf(request: FileRequest) -> AgentResponseWrapper:
    """Process  pdf, and transcribe."""
    try:
        transcription = FileService.extract_text_from_pdf(request.file_id, request.metadata)
        return AgentResponseWrapper(
            response=transcription
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
