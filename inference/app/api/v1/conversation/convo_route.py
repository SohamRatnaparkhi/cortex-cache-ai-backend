from fastapi import APIRouter
from pydantic import BaseModel

from app.services.Convo import get_citations_on_message_id, get_convo_summary

router = APIRouter(
    prefix='/convo',
)


class CitationBody(BaseModel):
    messageId: str
    title: str
    conversationId: str


@router.post('/citations')
async def get_citations_by_message_id(body: CitationBody):
    return await get_citations_on_message_id(body.messageId, body.title, body.conversationId)


@router.get('/summary/{conversation_id}')
async def get_summary(conversation_id: str):
    return await get_convo_summary(conversation_id)
