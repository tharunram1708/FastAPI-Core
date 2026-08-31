from fastapi import APIRouter

from app.api.v2.routes import health, items


router = APIRouter()
router.include_router(health.router, prefix="/health", tags=["v2:health"])
router.include_router(items.router, prefix="/items", tags=["v2:items"])
