import os
from typing import Dict, Optional

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.schemas.query.ApiModel import QueryRequest
from app.services.query import (stream_response, user_multi_query_service2,
                                user_query_service)
from app.utils.jwt import get_credentials

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
async def stream_llm_response(query: QueryRequest, request: Request):
    try:
        # get Authorization header
        header = request.headers.get("Authorization")
        # decode jwt token
        (userId, emailId, apiKey) = get_credentials(header)

        query.user_id = userId

        print("Query from user: ", query)

        obj = await user_query_service(query, is_stream=True)
        return StreamingResponse(stream_response(obj["prompt"], obj["messageId"], llm_type=query.llm or 'llama-3.1-70b'), media_type="text/event-stream")

    except Exception as e:
        print(e)
        print(query)
        return {"error": "Invalid JWT token"}
