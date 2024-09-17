from typing import Dict, Optional

from fastapi import APIRouter

from app.schemas.query.ApiModel import QueryRequest
from app.services.query import user_multi_query_service2, user_query_service

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
    return await user_query_service(query)