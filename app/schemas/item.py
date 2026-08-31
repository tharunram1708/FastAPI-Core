from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import re
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from app.schemas.response import ItemListMeta


RESERVED_ITEM_NAMES = {"admin", "root", "system"}
METADATA_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


def _normalize_name(value: str) -> str:
    name = " ".join(value.strip().split())
    if not name:
        raise ValueError("name cannot be blank")
    if name.casefold() in RESERVED_ITEM_NAMES:
        raise ValueError("name is reserved")
    return name


def _normalize_tags(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None

    normalized_tags: list[str] = []
    seen_tags: set[str] = set()
    for tag in value:
        normalized = tag.strip().casefold().replace(" ", "-")
        if not normalized:
            raise ValueError("tags cannot contain blank values")
        if normalized in seen_tags:
            raise ValueError("tags must be unique")
        seen_tags.add(normalized)
        normalized_tags.append(normalized)

    return normalized_tags


def _validate_metadata(value: dict[str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None

    for key, metadata_value in value.items():
        if not METADATA_KEY_PATTERN.fullmatch(key):
            raise ValueError("metadata keys must use snake_case")
        if not metadata_value.strip():
            raise ValueError("metadata values cannot be blank")

    return value


def _validate_description(name: str | None, description: str | None) -> None:
    if name and description and description.strip().casefold() == name.casefold():
        raise ValueError("description must add detail beyond the item name")


def _normalize_non_blank(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("value cannot be blank")
    return normalized


class ItemDimensions(BaseModel):
    length_cm: float = Field(gt=0, le=1000)
    width_cm: float = Field(gt=0, le=1000)
    height_cm: float = Field(gt=0, le=1000)

    @computed_field
    @property
    def volume_cm3(self) -> float:
        return round(self.length_cm * self.width_cm * self.height_cm, 2)


class ItemPricing(BaseModel):
    base_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    discount_percent: int = Field(default=0, ge=0, le=90)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        currency = value.strip().upper()
        if not currency.isalpha():
            raise ValueError("currency must contain only letters")
        return currency

    @model_validator(mode="after")
    def validate_discount(self) -> "ItemPricing":
        if self.base_price == 0 and self.discount_percent > 0:
            raise ValueError("discount_percent requires a positive base_price")
        return self

    @computed_field
    @property
    def final_price(self) -> Decimal:
        multiplier = Decimal(100 - self.discount_percent) / Decimal(100)
        return (self.base_price * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @field_serializer("base_price", "final_price", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ItemDetailBase(BaseModel):
    sku: str = Field(min_length=1, max_length=64)
    manufacturer: str | None = Field(default=None, max_length=120)
    origin_country: str | None = Field(default=None, max_length=80)
    warranty_months: int = Field(default=0, ge=0, le=600)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return _normalize_non_blank(value).upper()

    @field_validator("manufacturer", "origin_country")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_non_blank(value) if value is not None else None


class ItemDetailCreate(ItemDetailBase):
    pass


class ItemDetailRead(ItemDetailBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ItemReviewBase(BaseModel):
    reviewer_name: str = Field(min_length=1, max_length=120)
    rating: Decimal = Field(ge=0, le=5, max_digits=2, decimal_places=1)
    comment: str | None = Field(default=None, max_length=1000)

    @field_validator("reviewer_name")
    @classmethod
    def normalize_reviewer_name(cls, value: str) -> str:
        return _normalize_non_blank(value)

    @field_validator("comment")
    @classmethod
    def normalize_comment(cls, value: str | None) -> str | None:
        return _normalize_non_blank(value) if value is not None else None


class ItemReviewCreate(ItemReviewBase):
    pass


class ItemReviewRead(ItemReviewBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("rating", when_used="json")
    def serialize_rating(self, value: Decimal) -> str:
        return f"{value:.1f}"


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    contact_email: str | None = Field(default=None, max_length=255)
    website: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_non_blank(value)

    @field_validator("contact_email", "website")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _normalize_non_blank(value) if value is not None else None

    @field_validator("contact_email")
    @classmethod
    def validate_contact_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if "@" not in value or any(character.isspace() for character in value):
            raise ValueError("contact_email must be a valid email-like value")
        return value

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith(("http://", "https://")):
            raise ValueError("website must start with http:// or https://")
        return value


class SupplierCreate(SupplierBase):
    pass


class SupplierRead(SupplierBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ItemBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    category: str = Field(default="general", min_length=2, max_length=50)
    tags: list[str] = Field(default_factory=list, max_length=10)
    pricing: ItemPricing | None = None
    dimensions: ItemDimensions | None = None
    inventory_count: int = Field(default=0, ge=0, le=1_000_000)
    metadata: dict[str, str] = Field(default_factory=dict, max_length=20)
    rating: Decimal | None = Field(default=None, ge=0, le=5, max_digits=2, decimal_places=1)
    detail: ItemDetailCreate | None = None
    reviews: list[ItemReviewCreate] = Field(default_factory=list, max_length=20)
    suppliers: list[SupplierCreate] = Field(default_factory=list, max_length=10)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _normalize_name(value)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        return value.strip().casefold().replace(" ", "-")

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        return _normalize_tags(value) or []

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_metadata(value) or {}

    @field_validator("suppliers")
    @classmethod
    def validate_suppliers(cls, value: list[SupplierCreate]) -> list[SupplierCreate]:
        seen_suppliers: set[str] = set()
        for supplier in value:
            lookup_name = supplier.name.casefold()
            if lookup_name in seen_suppliers:
                raise ValueError("suppliers must be unique")
            seen_suppliers.add(lookup_name)
        return value

    @model_validator(mode="after")
    def validate_item(self) -> "ItemBase":
        _validate_description(self.name, self.description)
        if not self.is_active and self.inventory_count > 0:
            raise ValueError("inactive items cannot have inventory")
        return self


class ItemCreate(ItemBase):
    pass


class ItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    category: str | None = Field(default=None, min_length=2, max_length=50)
    tags: list[str] | None = Field(default=None, max_length=10)
    pricing: ItemPricing | None = None
    dimensions: ItemDimensions | None = None
    inventory_count: int | None = Field(default=None, ge=0, le=1_000_000)
    metadata: dict[str, str] | None = Field(default=None, max_length=20)
    rating: Decimal | None = Field(default=None, ge=0, le=5, max_digits=2, decimal_places=1)
    detail: ItemDetailCreate | None = None
    reviews: list[ItemReviewCreate] | None = Field(default=None, max_length=20)
    suppliers: list[SupplierCreate] | None = Field(default=None, max_length=10)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        return _normalize_name(value) if value is not None else None

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str | None) -> str | None:
        return value.strip().casefold().replace(" ", "-") if value is not None else None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        return _normalize_tags(value)

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return _validate_metadata(value)

    @field_validator("suppliers")
    @classmethod
    def validate_suppliers(
        cls,
        value: list[SupplierCreate] | None,
    ) -> list[SupplierCreate] | None:
        if value is None:
            return None

        seen_suppliers: set[str] = set()
        for supplier in value:
            lookup_name = supplier.name.casefold()
            if lookup_name in seen_suppliers:
                raise ValueError("suppliers must be unique")
            seen_suppliers.add(lookup_name)
        return value

    @model_validator(mode="after")
    def validate_item(self) -> "ItemPatch":
        _validate_description(self.name, self.description)
        if self.is_active is False and self.inventory_count and self.inventory_count > 0:
            raise ValueError("inactive items cannot have inventory")
        return self


ItemUpdate = ItemPatch


class ItemRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    category: str
    tags: list[str]
    pricing: ItemPricing | None
    dimensions: ItemDimensions | None
    inventory_count: int
    metadata: dict[str, str] = Field(
        validation_alias="item_metadata",
        serialization_alias="metadata",
    )
    rating: Decimal | None
    detail: ItemDetailRead | None = None
    reviews: list[ItemReviewRead] = Field(default_factory=list)
    suppliers: list[SupplierRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("rating", when_used="json")
    def serialize_rating(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        return f"{value:.1f}"

    @field_serializer("created_at", "updated_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.isoformat()

    @computed_field
    @property
    def availability(self) -> str:
        if not self.is_active:
            return "inactive"
        if self.inventory_count == 0:
            return "out_of_stock"
        return "available"


class ItemListResponse(BaseModel):
    data: list[ItemRead]
    meta: ItemListMeta
