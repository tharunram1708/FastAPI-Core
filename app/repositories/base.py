from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import (
    DatabaseConstraintViolationError,
    DatabaseTransactionError,
)
from app.db.pagination import Page, PaginationParams
from app.models.base import Base


ModelType = TypeVar("ModelType", bound=Base)


class SQLAlchemyRepository(Generic[ModelType]):
    def __init__(self, session: Session, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    def get(
        self,
        item_id: Any,
        *,
        options: Sequence[Any] | None = None,
    ) -> ModelType | None:
        try:
            return self.session.get(self.model, item_id, options=options)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseTransactionError() from exc

    def list(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Sequence[Any] | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ModelType]:
        statement = select(self.model).where(*(filters or ())).offset(skip).limit(limit)
        if options:
            statement = statement.options(*options)
        if order_by:
            statement = statement.order_by(*order_by)
        try:
            return list(self.session.scalars(statement))
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseTransactionError() from exc

    def paginate(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
        options: Sequence[Any] | None = None,
        order_by: Sequence[Any] | None = None,
        pagination: PaginationParams | None = None,
    ) -> Page[ModelType]:
        page_params = pagination or PaginationParams()
        items = self.list(
            filters=filters,
            options=options,
            order_by=order_by,
            skip=page_params.skip,
            limit=page_params.limit,
        )
        total = self.count(filters=filters)
        return Page(
            items=items,
            total=total,
            skip=page_params.skip,
            limit=page_params.limit,
        )

    def count(
        self,
        *,
        filters: Sequence[ColumnElement[bool]] | None = None,
    ) -> int:
        statement = select(func.count()).select_from(self.model).where(*(filters or ()))
        try:
            return self.session.scalar(statement) or 0
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseTransactionError() from exc

    def create(self, data: dict[str, Any]) -> ModelType:
        instance = self.model(**data)
        self.session.add(instance)
        self._flush()
        return instance

    def update(self, instance: ModelType, data: dict[str, Any]) -> ModelType:
        for field, value in data.items():
            setattr(instance, field, value)
        self._flush()
        return instance

    def delete(self, instance: ModelType) -> None:
        self.session.delete(instance)
        self._flush()

    def soft_delete(self, instance: ModelType) -> ModelType:
        now = datetime.now(timezone.utc)
        setattr(instance, "deleted_at", now)
        setattr(instance, "updated_at", now)
        self._flush()
        return instance

    def restore(self, instance: ModelType) -> ModelType:
        setattr(instance, "deleted_at", None)
        setattr(instance, "updated_at", datetime.now(timezone.utc))
        self._flush()
        return instance

    def exists(self, *filters: ColumnElement[bool]) -> bool:
        statement = select(self.model.id).where(*filters).limit(1)
        try:
            return self.session.scalar(statement) is not None
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseTransactionError() from exc

    def _flush(self) -> None:
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise DatabaseConstraintViolationError() from exc
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DatabaseTransactionError() from exc
