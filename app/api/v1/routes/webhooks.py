from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.schemas.enterprise import MessageResponse, WebhookEventCreate, WebhookEventRead


router = APIRouter()


@router.post("", response_model=WebhookEventRead, summary="Receive webhook event")
async def receive_webhook(
    payload: WebhookEventCreate,
    db: DatabaseSessionDep,
) -> WebhookEventRead:
    event = db.enterprise.webhook_events.create(payload.model_dump())
    try:
        if payload.payload.get("force_fail"):
            raise RuntimeError("forced webhook processing failure")
        event.status = "processed"
        event.attempts = 1
    except Exception as exc:
        event.status = "failed"
        event.attempts = 1
        event.last_error = str(exc)
        event.next_retry_at = db.enterprise.now() + timedelta(minutes=5)
    return event


@router.post("/{event_id}/retry", response_model=WebhookEventRead, summary="Retry failed webhook")
async def retry_webhook(
    event_id: UUID,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_WEBHOOKS))],
) -> WebhookEventRead:
    event = db.enterprise.webhook_events.get(event_id)
    if event is None:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Webhook event not found")
    event.attempts += 1
    event.status = "processed"
    event.next_retry_at = None
    event.last_error = None
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="RETRY_WEBHOOK",
        resource_type="webhook_event",
        resource_id=str(event.id),
    )
    return event


@router.get("/failed", response_model=list[WebhookEventRead], summary="List failed webhook events")
async def list_failed_webhooks(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.MANAGE_WEBHOOKS))],
) -> list[WebhookEventRead]:
    model = db.enterprise.webhook_events.model
    return db.enterprise.webhook_events.list(
        filters=(model.status == "failed",),
        order_by=(model.next_retry_at.asc(),),
        limit=100,
    )
