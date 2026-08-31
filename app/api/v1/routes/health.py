from fastapi import APIRouter
from sqlalchemy import text

from app.api.dependencies import DatabaseSessionDep
from app.schemas.health import HealthResponse
from app.schemas.enterprise import HealthDetailResponse
from app.services.health_service import get_health_status
from app.services.cache_service import cache


router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    return get_health_status()


@router.get("/ready", response_model=HealthDetailResponse, summary="Readiness check")
async def readiness_check(db: DatabaseSessionDep) -> HealthDetailResponse:
    checks: dict[str, str] = {}
    try:
        db.session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"

    checks["redis"] = cache.status()
    checks["external_api"] = "configured"
    status = "ok" if all(value in {"ok", "configured"} for value in checks.values()) else "degraded"
    health = get_health_status()
    return HealthDetailResponse(
        status=status,
        checks=checks,
        version=health.version,
        environment=health.environment,
    )
