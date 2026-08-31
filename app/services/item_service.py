from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.core.exceptions import DuplicateItemNameError
from app.db.pagination import Page, PaginationParams
from app.db.query import SortDirection, SortParams
from app.models.item import Item
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemPatch


class ItemService:
    def __init__(self, item_repository: ItemRepository) -> None:
        self.item_repository = item_repository

    def list_items(
        self,
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
        sort_by: str = "created_at",
        sort_order: SortDirection = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> list[Item]:
        return self.item_repository.list_items(
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
            sort=SortParams(sort_by=sort_by, sort_order=sort_order),
            skip=skip,
            limit=limit,
        )

    def paginate_items(
        self,
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
        sort_by: str = "created_at",
        sort_order: SortDirection = "desc",
        skip: int = 0,
        limit: int = 20,
    ) -> Page[Item]:
        return self.item_repository.paginate_items(
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
            sort=SortParams(sort_by=sort_by, sort_order=sort_order),
            pagination=PaginationParams(skip=skip, limit=limit),
        )

    def count_items(
        self,
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
        return self.item_repository.count_items(
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

    def get_item(self, item_id: UUID) -> Item | None:
        return self.item_repository.get_item(item_id)

    def create_item(self, payload: ItemCreate) -> Item:
        self._ensure_unique_name(payload.name)
        return self.item_repository.create_item(
            self._payload_data(payload),
            **self._relationship_data(payload),
        )

    def replace_item(self, item_id: UUID, payload: ItemCreate) -> Item | None:
        current = self.get_item(item_id)
        if current is None:
            return None

        self._ensure_unique_name(payload.name, exclude_item_id=item_id)
        update_data = self._payload_data(payload)
        update_data["updated_at"] = datetime.now(timezone.utc)
        current = self.item_repository.update_item(current, update_data)
        return self.item_repository.replace_relationships(
            current,
            **self._relationship_data(payload),
        )

    def update_item(self, item_id: UUID, payload: ItemPatch) -> Item | None:
        current = self.get_item(item_id)
        if current is None:
            return None

        update_data = self._payload_data(payload, exclude_unset=True)
        if "name" in update_data:
            self._ensure_unique_name(update_data["name"], exclude_item_id=item_id)

        relationship_data = self._relationship_data(payload, exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)
        current = self.item_repository.update_item(current, update_data)
        if relationship_data:
            current = self.item_repository.replace_relationships(current, **relationship_data)
        return current

    def delete_item(self, item_id: UUID) -> bool:
        item = self.get_item(item_id)
        if item is None:
            return False

        self.item_repository.delete_item(item)
        return True

    def restore_item(self, item_id: UUID) -> Item | None:
        item = self.item_repository.get_item_by_id(item_id, include_deleted=True)
        if item is None or item.deleted_at is None:
            return None

        return self.item_repository.restore_item(item)

    def _payload_data(
        self,
        payload: ItemCreate | ItemPatch,
        exclude_unset: bool = False,
    ) -> dict:
        data = self._model_data(payload, exclude_unset=exclude_unset)
        data.pop("detail", None)
        data.pop("reviews", None)
        data.pop("suppliers", None)
        return data

    def _relationship_data(
        self,
        payload: ItemCreate | ItemPatch,
        exclude_unset: bool = False,
    ) -> dict:
        data = self._model_data(payload, exclude_unset=exclude_unset)
        relationship_data = {}

        if "detail" in data:
            relationship_data["detail_data"] = data["detail"]
        if "reviews" in data:
            relationship_data["reviews_data"] = data["reviews"]
        if "suppliers" in data:
            relationship_data["suppliers_data"] = data["suppliers"]

        return relationship_data

    def _model_data(
        self,
        payload: ItemCreate | ItemPatch,
        exclude_unset: bool = False,
    ) -> dict:
        data = payload.model_dump(mode="json", exclude_unset=exclude_unset)
        if isinstance(data.get("pricing"), dict):
            data["pricing"].pop("final_price", None)
        if isinstance(data.get("dimensions"), dict):
            data["dimensions"].pop("volume_cm3", None)
        if "metadata" in data:
            data["item_metadata"] = data.pop("metadata")
        return data

    def _ensure_unique_name(
        self,
        name: str,
        exclude_item_id: UUID | None = None,
    ) -> None:
        if self.item_repository.name_exists(
            name,
            exclude_item_id=exclude_item_id,
        ):
            raise DuplicateItemNameError(name)
