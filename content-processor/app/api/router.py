from fastapi import APIRouter

from app.api.routers import v1_router

router = APIRouter(
    prefix='/api',
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

router.include_router(v1_router.router)