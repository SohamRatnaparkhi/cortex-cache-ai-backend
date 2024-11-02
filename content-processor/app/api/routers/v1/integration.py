from fastapi import APIRouter, HTTPException

from app.schemas.Common import AgentResponseWrapper
from app.schemas.Integration import NotionRequest
from app.services import NotionService

router = APIRouter(
    prefix='/integration',
    responses={404: {"description": "Not found in file route"}},
)


@router.post("/process/notion")
async def process_notion(request: NotionRequest) -> AgentResponseWrapper:
    try:
        response = await NotionService.extract_text_from_notion_page(access_token=request.access_token, resource_link=request.page_id, metadata=request.metadata)

        return AgentResponseWrapper(
            response=response
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
