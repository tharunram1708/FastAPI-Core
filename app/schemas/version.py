from app.schemas.health import HealthResponse


class VersionedHealthResponse(HealthResponse):
    api_version: str
