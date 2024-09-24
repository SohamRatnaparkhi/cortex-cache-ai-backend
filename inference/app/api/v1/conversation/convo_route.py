from fastapi import APIRouter

from app.services.Convo import get_citations_on_message_id

router = APIRouter(
    prefix='/convo',
)


@router.get('/citations/{message_id}')
async def get_citations_by_message_id(message_id: str):
    return await get_citations_on_message_id(message_id)
