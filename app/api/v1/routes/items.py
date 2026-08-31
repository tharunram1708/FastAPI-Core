from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request, Response, status

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, ItemListParamsDep, require_permissions
from app.core.authorization import Permission
from app.core.exceptions import ItemNotFoundError
from app.schemas.item import ItemCreate, ItemListResponse, ItemPatch, ItemRead
from app.schemas.response import ErrorResponse, ItemListMeta


router = APIRouter()


def _item_etag(item: ItemRead) -> str:
    version = item.updated_at or item.created_at
    return f'W/"{item.id}:{version.isoformat()}"'


@router.get(
    "",
    response_model=ItemListResponse,
    responses={
        status.HTTP_200_OK: {
            "description": "Items returned successfully.",
            "headers": {
                "X-Total-Count": {
                    "description": "Total matching items before pagination.",
                    "schema": {"type": "integer"},
                },
                "X-Skip": {
                    "description": "Pagination offset applied.",
                    "schema": {"type": "integer"},
                },
                "X-Limit": {
                    "description": "Pagination limit applied.",
                    "schema": {"type": "integer"},
                },
            },
        },
    },
    summary="List items",
)
async def list_items(
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
    responses={
        status.HTTP_200_OK: {
            "description": "Item returned successfully.",
            "headers": {
                "ETag": {
                    "description": "Weak entity tag for the item.",
                    "schema": {"type": "string"},
                },
                "Cache-Control": {
                    "description": "Client caching policy.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
    summary="Get item",
)
async def get_item(
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

    item_response = ItemRead.model_validate(item)
    response.headers["ETag"] = _item_etag(item_response)
    response.headers["Cache-Control"] = "private, max-age=60"
    return item


@router.post(
    "",
    response_model=ItemRead,
    response_model_exclude_none=True,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {
            "description": "Item created successfully.",
            "headers": {
                "Location": {
                    "description": "URL for the newly created item.",
                    "schema": {"type": "string"},
                },
                "X-Resource-ID": {
                    "description": "New item identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        422: {"description": "Validation error."},
    },
    summary="Create item",
)
async def create_item(
    payload: ItemCreate,
    request: Request,
    response: Response,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.CREATE_ITEM))],
) -> ItemRead:
    item = db.items.create_item(payload)
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="CREATE_ITEM",
        resource_type="item",
        resource_id=str(item.id),
        ip_address=request.client.host if request.client else None,
    )
    response.headers["Location"] = str(request.url_for("get_item", item_id=item.id))
    response.headers["X-Resource-ID"] = str(item.id)
    response.headers["X-Actor"] = current_user.username
    return item


@router.put(
    "/{item_id}",
    response_model=ItemRead,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {
            "description": "Item replaced successfully.",
            "headers": {
                "X-Resource-ID": {
                    "description": "Updated item identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
    summary="Replace item",
)
async def replace_item(
    response: Response,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.UPDATE_ITEM))],
    item_id: Annotated[
        UUID,
        Path(description="Unique item identifier."),
    ],
    payload: ItemCreate,
) -> ItemRead:
    previous = db.items.get_item(item_id)
    previous_data = (
        ItemRead.model_validate(previous).model_dump(mode="json")
        if previous is not None
        else {}
    )
    item = db.items.replace_item(item_id, payload)
    if item is None:
        raise ItemNotFoundError()
    if previous is not None:
        db.enterprise.create_history(
            resource_type="item",
            resource_id=str(previous.id),
            previous_data=previous_data,
            changed_by_id=current_user.id,
        )
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="UPDATE_ITEM",
        resource_type="item",
        resource_id=str(item.id),
    )

    response.headers["X-Resource-ID"] = str(item.id)
    response.headers["X-Actor"] = current_user.username
    return item


@router.patch(
    "/{item_id}",
    response_model=ItemRead,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {
            "description": "Item updated successfully.",
            "headers": {
                "X-Resource-ID": {
                    "description": "Updated item identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
    summary="Update item",
)
async def update_item(
    response: Response,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.UPDATE_ITEM))],
    item_id: Annotated[
        UUID,
        Path(description="Unique item identifier."),
    ],
    payload: ItemPatch,
) -> ItemRead:
    previous = db.items.get_item(item_id)
    previous_data = (
        ItemRead.model_validate(previous).model_dump(mode="json")
        if previous is not None
        else {}
    )
    item = db.items.update_item(item_id, payload)
    if item is None:
        raise ItemNotFoundError()
    if previous is not None:
        db.enterprise.create_history(
            resource_type="item",
            resource_id=str(previous.id),
            previous_data=previous_data,
            changed_by_id=current_user.id,
        )
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="UPDATE_ITEM",
        resource_type="item",
        resource_id=str(item.id),
    )

    response.headers["X-Resource-ID"] = str(item.id)
    response.headers["X-Actor"] = current_user.username
    return item


@router.post(
    "/{item_id}/restore",
    response_model=ItemRead,
    response_model_exclude_none=True,
    responses={
        status.HTTP_200_OK: {
            "description": "Item restored successfully.",
            "headers": {
                "X-Resource-ID": {
                    "description": "Restored item identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
    summary="Restore item",
)
async def restore_item(
    response: Response,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.UPDATE_ITEM))],
    item_id: Annotated[
        UUID,
        Path(description="Unique item identifier."),
    ],
) -> ItemRead:
    item = db.items.restore_item(item_id)
    if item is None:
        raise ItemNotFoundError()

    response.headers["X-Resource-ID"] = str(item.id)
    response.headers["X-Actor"] = current_user.username
    return item


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_204_NO_CONTENT: {
            "description": "Item deleted successfully.",
            "headers": {
                "X-Deleted-ID": {
                    "description": "Deleted item identifier.",
                    "schema": {"type": "string"},
                },
            },
        },
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    },
    summary="Delete item",
)
async def delete_item(
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.DELETE_ITEM))],
    item_id: Annotated[
        UUID,
        Path(description="Unique item identifier."),
    ],
) -> Response:
    deleted = db.items.delete_item(item_id)
    if not deleted:
        raise ItemNotFoundError()
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="DELETE_ITEM",
        resource_type="item",
        resource_id=str(item_id),
    )

    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={
            "X-Deleted-ID": str(item_id),
            "X-Actor": current_user.username,
        },
    )
