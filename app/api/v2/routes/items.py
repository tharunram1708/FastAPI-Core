from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status

from app.api.dependencies import DatabaseSessionDep, ItemListParamsDep
from app.core.exceptions import ItemNotFoundError
from app.schemas.item import ItemListResponse, ItemRead
from app.schemas.response import ErrorResponse, ItemListMeta


router = APIRouter()


@router.get(
    "",
    response_model=ItemListResponse,
    summary="List items v2",
)
async def list_items_v2(
    response: Response,
    db: DatabaseSessionDep,
    params: ItemListParamsDep,
) -> ItemListResponse:
    page = db.items.paginate_items(
        q=params.q,
        is_active=params.is_active,
        names=params.names,
        categories=params.categories,
        min_inventory_count=params.min_inventory_count,
        max_inventory_count=params.max_inventory_count,
        min_rating=params.min_rating,
        max_rating=params.max_rating,
        supplier_name=params.supplier_name,
        sort_by=params.sort_by,
        sort_order=params.sort_order,
        skip=params.skip,
        limit=params.limit,
    )

    response.headers["X-API-Version"] = "v2"
    response.headers["X-Total-Count"] = str(page.total)
    response.headers["X-Skip"] = str(page.skip)
    response.headers["X-Limit"] = str(page.limit)
    response.headers["Cache-Control"] = "no-store"

    return ItemListResponse(
        data=page.items,
        meta=ItemListMeta(
            total=page.total,
            skip=page.skip,
            limit=page.limit,
            returned=page.returned,
            has_next=page.has_next,
            has_previous=page.has_previous,
        ),
    )


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    response_model_exclude_none=True,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get item v2",
)
async def get_item_v2(
    response: Response,
    db: DatabaseSessionDep,
    item_id: Annotated[
        UUID,
        Path(description="Unique item identifier."),
    ],
) -> ItemRead:
    item = db.items.get_item(item_id)
    if item is None:
        raise ItemNotFoundError()

    response.headers["X-API-Version"] = "v2"
    response.headers["Cache-Control"] = "private, max-age=60"
    return item
