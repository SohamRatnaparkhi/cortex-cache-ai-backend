from fastapi import APIRouter

from app.api.v1.conversation import convo_route
from app.api.v1.query import query_route

router = APIRouter(
    prefix='/v1',
    tags=['v1']
)

router.include_router(router=query_route.router)
router.include_router(router=convo_route.router)
