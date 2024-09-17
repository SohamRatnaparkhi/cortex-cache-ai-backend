from fastapi import APIRouter

from app.api.v1 import v1_router

router = APIRouter(
    prefix='/api',
    tags=['api']
)

router.include_router(router=v1_router.router)