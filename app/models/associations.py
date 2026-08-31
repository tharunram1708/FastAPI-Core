from sqlalchemy import Column, ForeignKeyConstraint, Index, Table, Uuid

from app.models.base import Base


item_suppliers = Table(
    "item_suppliers",
    Base.metadata,
    Column(
        "item_id",
        Uuid(as_uuid=True),
        primary_key=True,
    ),
    Column(
        "supplier_id",
        Uuid(as_uuid=True),
        primary_key=True,
    ),
    ForeignKeyConstraint(
        ["item_id"],
        ["items.id"],
        name="fk_item_suppliers_item_id",
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["supplier_id"],
        ["suppliers.id"],
        name="fk_item_suppliers_supplier_id",
        ondelete="CASCADE",
    ),
    Index("ix_item_suppliers_item_id", "item_id"),
    Index("ix_item_suppliers_supplier_id", "supplier_id"),
)
