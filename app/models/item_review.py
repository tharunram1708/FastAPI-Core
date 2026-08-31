from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    ForeignKeyConstraint,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampedModel


class ItemReview(TimestampedModel, Base):
    __tablename__ = "item_reviews"
    __table_args__ = (
        ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_item_reviews_item_id",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "length(trim(reviewer_name)) > 0",
            name="ck_item_reviews_reviewer_name_not_blank",
        ),
        CheckConstraint("rating >= 0", name="ck_item_reviews_rating_min"),
        CheckConstraint("rating <= 5", name="ck_item_reviews_rating_max"),
        Index("ix_item_reviews_item_id", "item_id"),
        Index("ix_item_reviews_item_rating", "item_id", "rating"),
    )

    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
    )
    reviewer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    item: Mapped["Item"] = relationship("Item", back_populates="reviews")
