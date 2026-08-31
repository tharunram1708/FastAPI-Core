from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.db.pagination import Page, PaginationParams
from app.db.query import SortParams
from app.models.item_detail import ItemDetail
from app.models.item import Item
from app.models.item_review import ItemReview
from app.models.supplier import Supplier
from app.repositories.base import SQLAlchemyRepository


_UNSET = object()


class ItemRepository(SQLAlchemyRepository[Item]):
    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Item)

    def get_item(self, item_id: UUID) -> Item | None:
        return self.get_item_by_id(item_id)

    def get_item_by_id(
        self,
        item_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Item | None:
        item = self.get(item_id, options=self._relationship_loaders())
        if item is None:
            return None
        if not include_deleted and item.deleted_at is not None:
            return None
        return item

    def list_items(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        names: list[str] | None = None,
        categories: list[str] | None = None,
        min_inventory_count: int | None = None,
        max_inventory_count: int | None = None,
        min_rating: Decimal | None = None,
        max_rating: Decimal | None = None,
        supplier_name: str | None = None,
        include_deleted: bool = False,
        sort: SortParams | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Item]:
        return self.list(
            filters=self._filters(
                q=q,
                is_active=is_active,
                names=names,
                categories=categories,
                min_inventory_count=min_inventory_count,
                max_inventory_count=max_inventory_count,
                min_rating=min_rating,
                max_rating=max_rating,
                supplier_name=supplier_name,
                include_deleted=include_deleted,
            ),
            options=self._relationship_loaders(),
            order_by=self._sort_order(sort),
            skip=skip,
            limit=limit,
        )

    def paginate_items(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        names: list[str] | None = None,
        categories: list[str] | None = None,
        min_inventory_count: int | None = None,
        max_inventory_count: int | None = None,
        min_rating: Decimal | None = None,
        max_rating: Decimal | None = None,
        supplier_name: str | None = None,
        include_deleted: bool = False,
        sort: SortParams | None = None,
        pagination: PaginationParams | None = None,
    ) -> Page[Item]:
        return self.paginate(
            filters=self._filters(
                q=q,
                is_active=is_active,
                names=names,
                categories=categories,
                min_inventory_count=min_inventory_count,
                max_inventory_count=max_inventory_count,
                min_rating=min_rating,
                max_rating=max_rating,
                supplier_name=supplier_name,
                include_deleted=include_deleted,
            ),
            options=self._relationship_loaders(),
            order_by=self._sort_order(sort),
            pagination=pagination,
        )

    def count_items(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        names: list[str] | None = None,
        categories: list[str] | None = None,
        min_inventory_count: int | None = None,
        max_inventory_count: int | None = None,
        min_rating: Decimal | None = None,
        max_rating: Decimal | None = None,
        supplier_name: str | None = None,
        include_deleted: bool = False,
    ) -> int:
        return self.count(
            filters=self._filters(
                q=q,
                is_active=is_active,
                names=names,
                categories=categories,
                min_inventory_count=min_inventory_count,
                max_inventory_count=max_inventory_count,
                min_rating=min_rating,
                max_rating=max_rating,
                supplier_name=supplier_name,
                include_deleted=include_deleted,
            )
        )

    def name_exists(self, name: str, exclude_item_id: UUID | None = None) -> bool:
        filters: list[ColumnElement[bool]] = [func.lower(Item.name) == name.casefold()]
        if exclude_item_id is not None:
            filters.append(Item.id != exclude_item_id)
        return self.exists(*filters)

    def create_item(
        self,
        data: dict[str, Any],
        *,
        detail_data: dict[str, Any] | None = None,
        reviews_data: list[dict[str, Any]] | None = None,
        suppliers_data: list[dict[str, Any]] | None = None,
    ) -> Item:
        item = self.create(data)
        self.replace_relationships(
            item,
            detail_data=detail_data,
            reviews_data=reviews_data or [],
            suppliers_data=suppliers_data or [],
        )
        return item

    def update_item(
        self,
        item: Item,
        data: dict[str, Any],
    ) -> Item:
        return self.update(item, data)

    def delete_item(self, item: Item) -> None:
        self.soft_delete(item)

    def restore_item(self, item: Item) -> Item:
        return self.restore(item)

    def replace_relationships(
        self,
        item: Item,
        *,
        detail_data: dict[str, Any] | None | object = _UNSET,
        reviews_data: list[dict[str, Any]] | None = None,
        suppliers_data: list[dict[str, Any]] | None = None,
    ) -> Item:
        if detail_data is not _UNSET:
            if detail_data is None:
                item.detail = None
            elif item.detail is None:
                item.detail = ItemDetail(**detail_data)
            else:
                for field, value in detail_data.items():
                    setattr(item.detail, field, value)

        if reviews_data is not None:
            item.reviews = [ItemReview(**review_data) for review_data in reviews_data]

        if suppliers_data is not None:
            item.suppliers = [
                self._get_or_create_supplier(supplier_data)
                for supplier_data in suppliers_data
            ]

        self._flush()
        return item

    def _filters(
        self,
        *,
        q: str | None = None,
        is_active: bool | None = None,
        names: list[str] | None = None,
        categories: list[str] | None = None,
        min_inventory_count: int | None = None,
        max_inventory_count: int | None = None,
        min_rating: Decimal | None = None,
        max_rating: Decimal | None = None,
        supplier_name: str | None = None,
        include_deleted: bool = False,
    ) -> list[ColumnElement[bool]]:
        filters: list[ColumnElement[bool]] = []

        if not include_deleted:
            filters.append(Item.deleted_at.is_(None))

        if q is not None:
            search_text = f"%{q.casefold()}%"
            filters.append(
                or_(
                    func.lower(Item.name).like(search_text),
                    func.lower(Item.description).like(search_text),
                )
            )

        if is_active is not None:
            filters.append(Item.is_active.is_(is_active))

        if names:
            allowed_names = {name.casefold() for name in names}
            filters.append(func.lower(Item.name).in_(allowed_names))

        if categories:
            filters.append(Item.category.in_(categories))

        if min_inventory_count is not None:
            filters.append(Item.inventory_count >= min_inventory_count)

        if max_inventory_count is not None:
            filters.append(Item.inventory_count <= max_inventory_count)

        if min_rating is not None:
            filters.append(Item.rating >= min_rating)

        if max_rating is not None:
            filters.append(Item.rating <= max_rating)

        if supplier_name is not None:
            filters.append(
                Item.suppliers.any(
                    func.lower(Supplier.name) == supplier_name.casefold()
                )
            )

        return filters

    def _sort_order(self, sort: SortParams | None = None) -> tuple:
        sort_params = sort or SortParams()
        sort_columns = {
            "name": Item.name,
            "category": Item.category,
            "inventory_count": Item.inventory_count,
            "rating": Item.rating,
            "created_at": Item.created_at,
            "updated_at": Item.updated_at,
        }
        return (
            sort_params.resolve(sort_columns),
            Item.created_at.desc(),
            Item.name.asc(),
        )

    def _relationship_loaders(self) -> tuple:
        return (
            joinedload(Item.detail),
            selectinload(Item.reviews),
            selectinload(Item.suppliers),
        )

    def _get_or_create_supplier(self, supplier_data: dict[str, Any]) -> Supplier:
        supplier = self.session.scalar(
            select(Supplier).where(
                func.lower(Supplier.name) == supplier_data["name"].casefold()
            )
        )
        if supplier is not None:
            return supplier

        supplier = Supplier(**supplier_data)
        self.session.add(supplier)
        self._flush()
        return supplier
