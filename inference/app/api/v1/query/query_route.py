from typing import Dict, Optional

from fastapi import APIRouter

from app.schemas.query.ApiModel import QueryRequest
from app.services.query import user_multi_query_service2

router = APIRouter(
    prefix='/query',
    # tags=['query']
)

@router.post('/query')
async def handle_user_query(
    query: QueryRequest
):
    # return await user_query_service(query)
    print("query route called")
    print(query)
    return await user_multi_query_service2(query)