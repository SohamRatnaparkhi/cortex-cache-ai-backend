
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.schemas.query.query_related_types import QueryRequest
from app.services.query import process_user_query, stream_response
from app.utils.jwt import get_credentials

router = APIRouter(
    prefix='/query',
    # tags=['query']
)


@router.post('/single')
async def handle_user_query(
    query: QueryRequest
):
    return await process_user_query(query, is_stream=False)


@router.post("/stream")
async def stream_llm_response(query: QueryRequest, request: Request):
    try:
        # get Authorization header
        header = request.headers.get("Authorization")
        # decode jwt token
        (userId, emailId, apiKey) = get_credentials(header)

        query.user_id = userId

        obj = await process_user_query(query, is_stream=True)
        return StreamingResponse(stream_response(obj["prompt"], obj["messageId"], llm_type=query.llm or 'llama-3.1-70b'), media_type="text/event-stream")

    except Exception as e:
        print(e)
        print(query)
        return {"error": "Invalid JWT token"}
