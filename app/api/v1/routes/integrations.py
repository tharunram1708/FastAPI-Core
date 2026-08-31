import asyncio
import json
from urllib.request import Request, urlopen

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.enterprise import ExternalAPIResponse


router = APIRouter()


def _fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": settings.PROJECT_NAME})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@router.get("/external/status", response_model=ExternalAPIResponse, summary="Fetch external API status")
async def external_status() -> ExternalAPIResponse:
    try:
        data = await asyncio.to_thread(_fetch_json, settings.EXTERNAL_API_URL)
        transformed = {
            "service": settings.EXTERNAL_API_URL,
            "keys": sorted(data.keys())[:10] if isinstance(data, dict) else [],
        }
        return ExternalAPIResponse(source=settings.EXTERNAL_API_URL, ok=True, data=transformed)
    except Exception as exc:
        return ExternalAPIResponse(
            source=settings.EXTERNAL_API_URL,
            ok=False,
            data={"error": str(exc)},
        )


@router.get("/external/concurrent", response_model=list[ExternalAPIResponse], summary="Run concurrent external operations")
async def external_concurrent() -> list[ExternalAPIResponse]:
    urls = [settings.EXTERNAL_API_URL, settings.EXTERNAL_API_URL]
    results = await asyncio.gather(
        *(asyncio.to_thread(_fetch_json, url) for url in urls),
        return_exceptions=True,
    )
    responses: list[ExternalAPIResponse] = []
    for url, result in zip(urls, results, strict=True):
        if isinstance(result, Exception):
            responses.append(ExternalAPIResponse(source=url, ok=False, data={"error": str(result)}))
        else:
            responses.append(ExternalAPIResponse(source=url, ok=True, data={"type": type(result).__name__}))
    return responses
