from fastapi import APIRouter

from app.api.routers.v1 import audio, files, image, link

router = APIRouter(
    prefix='/v1',
    responses={404: {"description": "Not found in v1"}},
)

router.include_router(files.router)
router.include_router(link.router)
router.include_router(audio.router)
router.include_router(image.router)
    