from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.agents.TextAgent import TextAgent
from app.schemas.Common import AgentResponseWrapper
from app.schemas.Metadata import Metadata, NoteSpecificMd
from app.utils.app_logger_config import logger

router = APIRouter(
    prefix='/text',
    responses={404: {"description": "Not found in link route"}},
)


class TextRequest(BaseModel):
    text: str
    metadata: Metadata[NoteSpecificMd]


@router.post("/process/note")
async def process_text(request: TextRequest) -> AgentResponseWrapper:
    """Process text content and store it with embeddings."""
    try:
        # Initialize and process with TextAgent
        agent = TextAgent(text=request.text, md=request.metadata)
        response = await agent.process_media()

        return AgentResponseWrapper(
            response=response
        )
    except Exception as e:
        logger.error(f"Error processing text: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
