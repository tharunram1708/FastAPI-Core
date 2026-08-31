from sqlalchemy import CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.associations import item_suppliers
from app.models.base import Base, TimestampedModel


class Supplier(TimestampedModel, Base):
    __tablename__ = "suppliers"
    __table_args__ = (
        UniqueConstraint("name", name="uq_suppliers_name"),
        CheckConstraint("length(trim(name)) > 0", name="ck_suppliers_name_not_blank"),
        CheckConstraint(
            "contact_email IS NULL OR contact_email LIKE '%@%'",
            name="ck_suppliers_contact_email_has_at",
        ),
        CheckConstraint(
            "website IS NULL OR website LIKE 'http://%' OR website LIKE 'https://%'",
            name="ck_suppliers_website_url",
        ),
        Index("ix_suppliers_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    items: Mapped[list["Item"]] = relationship(
        "Item",
        secondary=item_suppliers,
        back_populates="suppliers",
    )
