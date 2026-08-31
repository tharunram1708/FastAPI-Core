from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Response, status

from app.api.dependencies import DatabaseSessionDep, require_permissions
from app.core.authorization import Permission, effective_permissions
from app.core.exceptions import ResourceNotFoundError
from app.schemas.response import ErrorResponse
from app.schemas.user import RolePermissionsResponse, UserRead, UserUpdate


router = APIRouter()


@router.get(
    "",
    response_model=list[UserRead],
    response_model_exclude_none=True,
    summary="List users",
)
async def list_users(
    db: DatabaseSessionDep,
    _actor: Annotated[object, Depends(require_permissions(Permission.READ_USER))],
    skip: int = 0,
    limit: int = 100,
) -> list[UserRead]:
    return db.user_repository.list_users(skip=skip, limit=limit)


@router.get(
    "/roles/{role}/permissions",
    response_model=RolePermissionsResponse,
    summary="Get role permissions",
)
async def get_role_permissions(role: str) -> RolePermissionsResponse:
    return RolePermissionsResponse(
        role=role.upper(),
        permissions=sorted(effective_permissions(role.upper())),
    )


@router.get(
    "/{user_id}",
    response_model=UserRead,
    response_model_exclude_none=True,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Get user",
)
async def get_user(
    db: DatabaseSessionDep,
    _actor: Annotated[object, Depends(require_permissions(Permission.READ_USER))],
    user_id: Annotated[UUID, Path(description="User identifier.")],
) -> UserRead:
    user = db.user_repository.get_user(user_id)
    if user is None:
        raise ResourceNotFoundError("User not found")
    return user


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    response_model_exclude_none=True,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Update user role, permissions, or status",
)
async def update_user(
    payload: UserUpdate,
    db: DatabaseSessionDep,
    actor: Annotated[object, Depends(require_permissions(Permission.UPDATE_USER))],
    user_id: Annotated[UUID, Path(description="User identifier.")],
) -> UserRead:
    user = db.user_repository.get_user(user_id)
    if user is None:
        raise ResourceNotFoundError("User not found")
    data = payload.model_dump(exclude_unset=True, mode="json")
    if "role" in data and data["role"] is not None:
        data["role"] = data["role"].upper()
    db.enterprise.create_history(
        resource_type="user",
        resource_id=str(user.id),
        previous_data={
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "role": user.role,
            "permissions": user.permissions,
        },
        changed_by_id=getattr(actor, "id", None),
    )
    updated = db.user_repository.update_user(user, data)
    db.enterprise.create_audit_log(
        actor_id=getattr(actor, "id", None),
        action="UPDATE_USER",
        resource_type="user",
        resource_id=str(user.id),
    )
    return updated


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
    summary="Deactivate user",
)
async def delete_user(
    db: DatabaseSessionDep,
    actor: Annotated[object, Depends(require_permissions(Permission.DELETE_USER))],
    user_id: Annotated[UUID, Path(description="User identifier.")],
) -> Response:
    user = db.user_repository.get_user(user_id)
    if user is None:
        raise ResourceNotFoundError("User not found")
    db.user_repository.update_user(user, {"is_active": False})
    db.enterprise.revoke_user_sessions(user.id)
    db.refresh_token_repository.revoke_all_for_user(user.id)
    db.enterprise.create_audit_log(
        actor_id=getattr(actor, "id", None),
        action="DELETE_USER",
        resource_type="user",
        resource_id=str(user.id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
