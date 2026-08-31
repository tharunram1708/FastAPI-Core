from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.schemas.enterprise import (
    BulkDeleteRequest,
    BulkItemCreateRequest,
    BulkItemUpdateRequest,
    BulkOperationResponse,
)
from app.schemas.item import ItemRead
from app.services.cache_service import cache


router = APIRouter()


@router.post("/items", response_model=BulkOperationResponse, summary="Bulk create items")
async def bulk_create_items(
    payload: BulkItemCreateRequest,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.BULK_OPERATIONS))],
) -> BulkOperationResponse:
    response = BulkOperationResponse()
    for index, item_payload in enumerate(payload.items):
        try:
            item = db.items.create_item(item_payload)
            db.enterprise.create_audit_log(
                actor_id=current_user.id,
                action="BULK_CREATE_ITEM",
                resource_type="item",
                resource_id=str(item.id),
            )
            response.created += 1
        except Exception as exc:
            response.failed += 1
            response.errors.append({"index": index, "error": str(exc)})
    cache.invalidate_prefix("search:items:")
    return response


@router.patch("/items", response_model=BulkOperationResponse, summary="Bulk update items")
async def bulk_update_items(
    payload: BulkItemUpdateRequest,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.BULK_OPERATIONS))],
) -> BulkOperationResponse:
    response = BulkOperationResponse()
    for index, item_update in enumerate(payload.items):
        try:
            previous = db.items.get_item(item_update.id)
            previous_data = (
                ItemRead.model_validate(previous).model_dump(mode="json")
                if previous is not None
                else {}
            )
            item = db.items.update_item(item_update.id, item_update.data)
            if item is None:
                raise ValueError("item not found")
            db.enterprise.create_history(
                resource_type="item",
                resource_id=str(item.id),
                previous_data=previous_data,
                changed_by_id=current_user.id,
            )
            response.updated += 1
        except Exception as exc:
            response.failed += 1
            response.errors.append({"index": index, "id": str(item_update.id), "error": str(exc)})
    cache.invalidate_prefix("search:items:")
    return response


@router.delete("/items", response_model=BulkOperationResponse, summary="Bulk delete items")
async def bulk_delete_items(
    payload: BulkDeleteRequest,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.BULK_OPERATIONS))],
) -> BulkOperationResponse:
    response = BulkOperationResponse()
    for item_id in payload.ids:
        if db.items.delete_item(item_id):
            response.deleted += 1
            db.enterprise.create_audit_log(
                actor_id=current_user.id,
                action="BULK_DELETE_ITEM",
                resource_type="item",
                resource_id=str(item_id),
            )
        else:
            response.failed += 1
            response.errors.append({"id": str(item_id), "error": "item not found"})
    cache.invalidate_prefix("search:items:")
    return response
