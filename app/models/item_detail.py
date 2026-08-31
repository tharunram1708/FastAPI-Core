from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel


class ItemDetail(TimestampedModel, Base):
    __tablename__ = "item_details"
    __table_args__ = (
        UniqueConstraint("item_id", name="uq_item_details_item_id"),
        UniqueConstraint("sku", name="uq_item_details_sku"),
        ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_item_details_item_id",
            ondelete="CASCADE",
        ),
        CheckConstraint("length(trim(sku)) > 0", name="ck_item_details_sku_not_blank"),
        CheckConstraint(
            "warranty_months >= 0",
            name="ck_item_details_warranty_non_negative",
        ),
        CheckConstraint("warranty_months <= 600", name="ck_item_details_warranty_max"),
        Index("ix_item_details_item_id", "item_id"),
        Index("ix_item_details_sku", "sku"),
    )

    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(64), nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin_country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    warranty_months: Mapped[int] = mapped_column(default=0, nullable=False)

    item: Mapped["Item"] = relationship("Item", back_populates="detail")
