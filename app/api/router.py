from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.api.v2.router import router as v2_router
from app.core.config import settings


router = APIRouter()
router.include_router(v1_router, prefix=settings.API_V1_PREFIX)
router.include_router(v2_router, prefix=settings.API_V2_PREFIX)
