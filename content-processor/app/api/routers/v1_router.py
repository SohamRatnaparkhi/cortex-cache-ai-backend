from fastapi import APIRouter

from app.api.routers.v1 import files, integration, link, text

router = APIRouter(
    prefix='/v1',
    responses={404: {"description": "Not found in v1"}},
)

router.include_router(files.router)
router.include_router(link.router)
router.include_router(integration.router)
router.include_router(text.router)
# router.include_router(audio.router)
# router.include_router(image.router)
# router.include_router(video.router)
