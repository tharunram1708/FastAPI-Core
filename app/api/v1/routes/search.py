from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.schemas.enterprise import SearchResponse
from app.schemas.item import ItemRead
from app.services.cache_service import cache


router = APIRouter()


@router.get("/items", response_model=SearchResponse, summary="Advanced item search")
async def search_items(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.READ_ITEM))],
    q: str,
    category: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 20,
) -> SearchResponse:
    cache_key = f"search:items:{q}:{category}:{sort_by}:{sort_order}:{skip}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    rows = db.enterprise.search_items(
        q=q,
        category=category,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit,
    )
    response = SearchResponse(
        data=[ItemRead.model_validate(item).model_dump(mode="json") for item in rows],
        total=len(rows),
        skip=skip,
        limit=limit,
    )
    cache.set(cache_key, response, ttl_seconds=60)
    return response
