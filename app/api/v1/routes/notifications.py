from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from app.api.dependencies import CurrentActiveUserDep, CurrentUserDep, DatabaseSessionDep, require_roles
from app.core.authorization import Role
from app.schemas.enterprise import MessageResponse, NotificationCreate, NotificationRead


router = APIRouter()


def _simulate_delivery(notification_id: UUID) -> None:
    return None


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED, summary="Create notification")
async def create_notification(
    payload: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _role: Annotated[object, Depends(require_roles(Role.ADMIN, Role.MANAGER))],
) -> NotificationRead:
    notification = db.enterprise.create_notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        category=payload.category,
        metadata=payload.metadata,
    )
    background_tasks.add_task(_simulate_delivery, notification.id)
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="CREATE_NOTIFICATION",
        resource_type="notification",
        resource_id=str(notification.id),
    )
    return notification


@router.get("", response_model=list[NotificationRead], summary="List my notifications")
async def list_notifications(
    current_user: CurrentActiveUserDep,
    db: DatabaseSessionDep,
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 100,
) -> list[NotificationRead]:
    filters = [db.enterprise.notifications.model.user_id == current_user.id]
    if unread_only:
        filters.append(db.enterprise.notifications.model.read_at.is_(None))
    return db.enterprise.notifications.list(filters=filters, order_by=(db.enterprise.notifications.model.created_at.desc(),), skip=skip, limit=limit)


@router.post("/{notification_id}/read", response_model=NotificationRead, summary="Mark notification read")
async def mark_read(
    notification_id: UUID,
    current_user: CurrentActiveUserDep,
    db: DatabaseSessionDep,
) -> NotificationRead:
    notification = db.enterprise.notifications.get(notification_id)
    if notification is None or notification.user_id != current_user.id:
        from app.core.exceptions import ResourceNotFoundError

        raise ResourceNotFoundError("Notification not found")
    notification.read_at = datetime.now(timezone.utc)
    return notification


@router.post("/mark-all-read", response_model=MessageResponse, summary="Mark all notifications read")
async def mark_all_read(
    current_user: CurrentActiveUserDep,
    db: DatabaseSessionDep,
) -> MessageResponse:
    now = datetime.now(timezone.utc)
    notifications = db.enterprise.notifications.list(
        filters=(
            db.enterprise.notifications.model.user_id == current_user.id,
            db.enterprise.notifications.model.read_at.is_(None),
        ),
        limit=1000,
    )
    for notification in notifications:
        notification.read_at = now
    return MessageResponse(message=f"{len(notifications)} notifications marked read")
