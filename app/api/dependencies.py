from decimal import Decimal
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Annotated, Callable, Literal
from uuid import UUID

from fastapi import Depends, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.config import settings
from app.core.authorization import Permission, Role, effective_permissions
from app.core.exceptions import (
    AccessTokenError,
    AuthenticationError,
    AuthorizationError,
    InactiveUserError,
    RateLimitExceededError,
)
from app.core.security import decode_access_token
from app.db.session import DatabaseSession, get_database_session
from app.models.user import User


class CurrentUser(BaseModel):
    id: UUID | None = None
    username: str
    email: str | None = None
    role: str = "api-client"
    scopes: list[str] = Field(default_factory=list)


class ItemListParams(BaseModel):
    q: str | None = Field(default=None, min_length=1, max_length=120)
    is_active: bool | None = None
    names: list[str] | None = None
    categories: list[str] | None = None
    min_inventory_count: int | None = Field(default=None, ge=0)
    max_inventory_count: int | None = Field(default=None, ge=0)
    min_rating: Decimal | None = Field(default=None, ge=0, le=5, max_digits=2, decimal_places=1)
    max_rating: Decimal | None = Field(default=None, ge=0, le=5, max_digits=2, decimal_places=1)
    supplier_name: str | None = Field(default=None, min_length=1, max_length=120)
    sort_by: Literal[
        "name",
        "category",
        "inventory_count",
        "rating",
        "created_at",
        "updated_at",
    ] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

    @model_validator(mode="after")
    def validate_filters(self) -> "ItemListParams":
        if self.names:
            normalized_names = []
            seen_names = set()
            for name in self.names:
                normalized_name = " ".join(name.strip().split())
                if not normalized_name:
                    raise ValueError("names cannot contain blank values")
                lookup_name = normalized_name.casefold()
                if lookup_name in seen_names:
                    raise ValueError("names must be unique")
                seen_names.add(lookup_name)
                normalized_names.append(normalized_name)
            self.names = normalized_names

        if self.categories:
            normalized_categories = []
            seen_categories = set()
            for category in self.categories:
                normalized_category = category.strip().casefold().replace(" ", "-")
                if not normalized_category:
                    raise ValueError("categories cannot contain blank values")
                if normalized_category in seen_categories:
                    raise ValueError("categories must be unique")
                seen_categories.add(normalized_category)
                normalized_categories.append(normalized_category)
            self.categories = normalized_categories

        if self.supplier_name is not None:
            self.supplier_name = " ".join(self.supplier_name.strip().split())
            if not self.supplier_name:
                raise ValueError("supplier_name cannot be blank")

        if (
            self.min_inventory_count is not None
            and self.max_inventory_count is not None
            and self.min_inventory_count > self.max_inventory_count
        ):
            raise ValueError("min_inventory_count cannot exceed max_inventory_count")

        if (
            self.min_rating is not None
            and self.max_rating is not None
            and self.min_rating > self.max_rating
        ):
            raise ValueError("min_rating cannot exceed max_rating")

        return self


def get_current_user(
    db: Annotated[DatabaseSession, Depends(get_database_session)],
    authorization: Annotated[
        str | None,
        Header(
            alias="Authorization",
            description="Bearer access token returned by /api/v1/auth/login.",
        ),
    ] = None,
    x_api_key: Annotated[
        str | None,
        Header(
            alias="X-API-Key",
            description="Legacy API key accepted for write operations.",
        ),
    ] = None,
) -> CurrentUser:
    if authorization is not None:
        user = _get_user_from_authorization_header(authorization, db)
        return CurrentUser(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            scopes=sorted(effective_permissions(user.role, user.permissions)),
        )

    if x_api_key and x_api_key == settings.API_KEY:
        return CurrentUser(
            username="api-client",
            role=Role.ADMIN.value,
            scopes=sorted(effective_permissions(Role.ADMIN.value)),
        )

    raise AuthenticationError()


def get_current_active_user(
    db: Annotated[DatabaseSession, Depends(get_database_session)],
    authorization: Annotated[
        str | None,
        Header(
            alias="Authorization",
            description="Bearer access token returned by /api/v1/auth/login.",
        ),
    ] = None,
) -> User:
    if authorization is None:
        raise AccessTokenError()

    return _get_user_from_authorization_header(authorization, db)


get_authenticated_user = get_current_active_user


def _get_user_from_authorization_header(
    authorization: str,
    db: DatabaseSession,
) -> User:
    scheme, separator, token = authorization.strip().partition(" ")
    if not separator or scheme.casefold() != "bearer" or not token:
        raise AccessTokenError()

    payload = decode_access_token(token, secret_key=settings.AUTH_SECRET_KEY)
    if payload is None or payload.get("type") != "access":
        raise AccessTokenError()

    subject = payload.get("sub")
    if not isinstance(subject, str):
        raise AccessTokenError()

    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise AccessTokenError() from exc

    user = db.user_repository.get_user(user_id)
    if user is None:
        raise AccessTokenError()
    if not user.is_active:
        raise InactiveUserError()
    session_id = payload.get("sid")
    if session_id is not None:
        try:
            active_session_id = UUID(session_id)
        except (TypeError, ValueError) as exc:
            raise AccessTokenError() from exc
        if db.enterprise.active_user_session(active_session_id) is None:
            raise AccessTokenError()

    return user


def require_roles(*roles: Role | str) -> Callable:
    allowed_roles = {str(role).upper() for role in roles}

    def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role.upper() not in allowed_roles:
            raise AuthorizationError()
        return current_user

    return dependency


def require_permissions(*permissions: Permission | str) -> Callable:
    required_permissions = {str(permission).upper() for permission in permissions}

    def dependency(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        user_permissions = effective_permissions(current_user.role, current_user.scopes)
        if not required_permissions.issubset(user_permissions):
            raise AuthorizationError()
        return current_user

    return dependency


_rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    now = datetime.now(timezone.utc).timestamp()
    client_host = request.client.host if request.client else "unknown"
    bucket = _rate_limit_buckets[client_host]
    while bucket and bucket[0] <= now - 60:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_PER_MINUTE:
        raise RateLimitExceededError()
    bucket.append(now)


def get_item_list_params(
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Optional search text matched against item name and description.",
        ),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(description="Optional active-state filter."),
    ] = None,
    names: Annotated[
        list[str] | None,
        Query(description="Optional repeated query parameter for exact item names."),
    ] = None,
    categories: Annotated[
        list[str] | None,
        Query(description="Optional repeated query parameter for item categories."),
    ] = None,
    min_inventory_count: Annotated[
        int | None,
        Query(ge=0, description="Minimum inventory count."),
    ] = None,
    max_inventory_count: Annotated[
        int | None,
        Query(ge=0, description="Maximum inventory count."),
    ] = None,
    min_rating: Annotated[
        Decimal | None,
        Query(ge=0, le=5, description="Minimum item rating."),
    ] = None,
    max_rating: Annotated[
        Decimal | None,
        Query(ge=0, le=5, description="Maximum item rating."),
    ] = None,
    supplier_name: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Optional case-insensitive supplier name filter.",
        ),
    ] = None,
    sort_by: Annotated[
        Literal[
            "name",
            "category",
            "inventory_count",
            "rating",
            "created_at",
            "updated_at",
        ],
        Query(description="Allowlisted field used to sort item results."),
    ] = "created_at",
    sort_order: Annotated[
        Literal["asc", "desc"],
        Query(description="Sort direction."),
    ] = "desc",
    skip: Annotated[
        int,
        Query(ge=0, description="Number of matching items to skip."),
    ] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum number of matching items to return."),
    ] = 20,
) -> ItemListParams:
    try:
        return ItemListParams(
            q=q,
            is_active=is_active,
            names=names,
            categories=categories,
            min_inventory_count=min_inventory_count,
            max_inventory_count=max_inventory_count,
            min_rating=min_rating,
            max_rating=max_rating,
            supplier_name=supplier_name,
            sort_by=sort_by,
            sort_order=sort_order,
            skip=skip,
            limit=limit,
        )
    except ValidationError as exc:
        raise RequestValidationError(
            exc.errors(include_url=False, include_context=False)
        ) from exc


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
AuthenticatedUserDep = Annotated[User, Depends(get_current_active_user)]
CurrentActiveUserDep = AuthenticatedUserDep
DatabaseSessionDep = Annotated[DatabaseSession, Depends(get_database_session)]
ItemListParamsDep = Annotated[ItemListParams, Depends(get_item_list_params)]
