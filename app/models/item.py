from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import item_suppliers
from app.models.base import Base, SoftDeleteModel, TimestampedModel


class Item(SoftDeleteModel, TimestampedModel, Base):
    __tablename__ = "items"
    __table_args__ = (
        UniqueConstraint("name", name="uq_items_name"),
        CheckConstraint("length(trim(name)) > 0", name="ck_items_name_not_blank"),
        CheckConstraint(
            "length(trim(category)) > 0",
            name="ck_items_category_not_blank",
        ),
        CheckConstraint(
            "inventory_count >= 0",
            name="ck_items_inventory_count_non_negative",
        ),
        CheckConstraint(
            "inventory_count <= 1000000",
            name="ck_items_inventory_count_max",
        ),
        CheckConstraint(
            "is_active = TRUE OR inventory_count = 0",
            name="ck_items_inactive_has_no_inventory",
        ),
        CheckConstraint(
            "rating IS NULL OR rating >= 0",
            name="ck_items_rating_min",
        ),
        CheckConstraint(
            "rating IS NULL OR rating <= 5",
            name="ck_items_rating_max",
        ),
        CheckConstraint(
            "rating IS NULL OR rating BETWEEN 0 AND 5",
            name="ck_items_rating_range",
        ),
        Index("ix_items_name", "name"),
        Index("ix_items_category", "category"),
        Index("ix_items_active_category", "is_active", "category"),
        Index("ix_items_inventory_count", "inventory_count"),
        Index("ix_items_rating", "rating"),
        Index("ix_items_created_at", "created_at"),
        Index("ix_items_deleted_at", "deleted_at"),
        Index("ix_items_deleted_active_category", "deleted_at", "is_active", "category"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
    )
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    pricing: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    inventory_count: Mapped[int] = mapped_column(default=0, nullable=False)
    item_metadata: Mapped[dict[str, str]] = mapped_column(
        "metadata",
        JSON,
        default=dict,
        nullable=False,
    )
    rating: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)

    detail: Mapped["ItemDetail | None"] = relationship(
        "ItemDetail",
        back_populates="item",
        cascade="all, delete-orphan",
        uselist=False,
    )
    reviews: Mapped[list["ItemReview"]] = relationship(
        "ItemReview",
        back_populates="item",
        cascade="all, delete-orphan",
    )
    suppliers: Mapped[list["Supplier"]] = relationship(
        "Supplier",
        secondary=item_suppliers,
        back_populates="items",
    )
