from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import DatabaseSessionDep, require_permissions
from app.core.authorization import Permission
from app.schemas.enterprise import AuditLogRead, RecordHistoryRead


router = APIRouter()


@router.get("/logs", response_model=list[AuditLogRead], summary="List audit logs")
async def list_audit_logs(
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.VIEW_AUDIT_LOGS))],
    action: str | None = None,
    resource_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AuditLogRead]:
    return db.enterprise.list_audit_logs(
        action=action,
        resource_type=resource_type,
        skip=skip,
        limit=limit,
    )


@router.get("/history/{resource_type}/{resource_id}", response_model=list[RecordHistoryRead], summary="List record history")
async def list_record_history(
    resource_type: str,
    resource_id: str,
    db: DatabaseSessionDep,
    _permission: Annotated[object, Depends(require_permissions(Permission.VIEW_AUDIT_LOGS))],
) -> list[RecordHistoryRead]:
    model = db.enterprise.record_history.model
    return db.enterprise.record_history.list(
        filters=(model.resource_type == resource_type, model.resource_id == resource_id),
        order_by=(model.version.desc(),),
        limit=100,
    )
