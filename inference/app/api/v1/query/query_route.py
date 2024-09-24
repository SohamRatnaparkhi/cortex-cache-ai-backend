from typing import Dict, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.query.ApiModel import QueryRequest
from app.services.query import (stream_response, user_multi_query_service2,
                                user_query_service)

router = APIRouter(
    prefix='/query',
    # tags=['query']
)


@router.post('/multiple')
async def handle_user_query(
    query: QueryRequest
):
    # return await user_query_service(query)
    return await user_multi_query_service2(query)


@router.post('/single')
async def handle_user_query(
    query: QueryRequest
):
    return await user_query_service(query, is_stream=False)


@router.post("/stream")
async def stream_llm_response(query: QueryRequest):
    print(f"Query: {query}")
    obj = await user_query_service(query, is_stream=True)
    print(f"Obj: {obj}")
    return StreamingResponse(stream_response(obj["prompt"], obj["messageId"]), media_type="text/event-stream")
