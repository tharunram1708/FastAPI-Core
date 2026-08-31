from fastapi import APIRouter

from app.schemas.version import VersionedHealthResponse
from app.services.health_service import get_health_status


router = APIRouter()


@router.get("", response_model=VersionedHealthResponse, summary="Health check v2")
async def health_check_v2() -> VersionedHealthResponse:
    health = get_health_status()
    return VersionedHealthResponse(
        api_version="v2",
        status=health.status,
        environment=health.environment,
        version=health.version,
    )
