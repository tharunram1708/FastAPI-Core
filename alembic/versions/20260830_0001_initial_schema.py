"""Initial schema

Revision ID: 20260830_0001
Revises:
Create Date: 2026-08-30 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260830_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "items",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("pricing", sa.JSON(), nullable=True),
        sa.Column("dimensions", sa.JSON(), nullable=True),
        sa.Column("inventory_count", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "inventory_count <= 1000000",
            name="ck_items_inventory_count_max",
        ),
        sa.CheckConstraint(
            "inventory_count >= 0",
            name="ck_items_inventory_count_non_negative",
        ),
        sa.CheckConstraint(
            "is_active = TRUE OR inventory_count = 0",
            name="ck_items_inactive_has_no_inventory",
        ),
        sa.CheckConstraint(
            "length(trim(category)) > 0",
            name="ck_items_category_not_blank",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_items_name_not_blank"),
        sa.CheckConstraint(
            "rating IS NULL OR rating <= 5",
            name="ck_items_rating_max",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR rating >= 0",
            name="ck_items_rating_min",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 0 AND 5",
            name="ck_items_rating_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_items_name"),
    )
    op.create_index("ix_items_active_category", "items", ["is_active", "category"])
    op.create_index("ix_items_category", "items", ["category"])
    op.create_index("ix_items_created_at", "items", ["created_at"])
    op.create_index("ix_items_deleted_active_category", "items", ["deleted_at", "is_active", "category"])
    op.create_index("ix_items_deleted_at", "items", ["deleted_at"])
    op.create_index("ix_items_inventory_count", "items", ["inventory_count"])
    op.create_index("ix_items_name", "items", ["name"])
    op.create_index("ix_items_rating", "items", ["rating"])

    op.create_table(
        "suppliers",
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "contact_email IS NULL OR contact_email LIKE '%@%'",
            name="ck_suppliers_contact_email_has_at",
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_suppliers_name_not_blank"),
        sa.CheckConstraint(
            "website IS NULL OR website LIKE 'http://%' OR website LIKE 'https://%'",
            name="ck_suppliers_website_url",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_suppliers_name"),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])

    op.create_table(
        "item_details",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=64), nullable=False),
        sa.Column("manufacturer", sa.String(length=120), nullable=True),
        sa.Column("origin_country", sa.String(length=80), nullable=True),
        sa.Column("warranty_months", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(sku)) > 0", name="ck_item_details_sku_not_blank"),
        sa.CheckConstraint(
            "warranty_months >= 0",
            name="ck_item_details_warranty_non_negative",
        ),
        sa.CheckConstraint(
            "warranty_months <= 600",
            name="ck_item_details_warranty_max",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_item_details_item_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", name="uq_item_details_item_id"),
        sa.UniqueConstraint("sku", name="uq_item_details_sku"),
    )
    op.create_index("ix_item_details_item_id", "item_details", ["item_id"])
    op.create_index("ix_item_details_sku", "item_details", ["sku"])

    op.create_table(
        "item_reviews",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_name", sa.String(length=120), nullable=False),
        sa.Column("rating", sa.Numeric(2, 1), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "length(trim(reviewer_name)) > 0",
            name="ck_item_reviews_reviewer_name_not_blank",
        ),
        sa.CheckConstraint("rating <= 5", name="ck_item_reviews_rating_max"),
        sa.CheckConstraint("rating >= 0", name="ck_item_reviews_rating_min"),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_item_reviews_item_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_item_reviews_item_id", "item_reviews", ["item_id"])
    op.create_index("ix_item_reviews_item_rating", "item_reviews", ["item_id", "rating"])

    op.create_table(
        "item_suppliers",
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="fk_item_suppliers_item_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_item_suppliers_supplier_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("item_id", "supplier_id"),
    )
    op.create_index("ix_item_suppliers_item_id", "item_suppliers", ["item_id"])
    op.create_index("ix_item_suppliers_supplier_id", "item_suppliers", ["supplier_id"])


def downgrade() -> None:
    op.drop_index("ix_item_suppliers_supplier_id", table_name="item_suppliers")
    op.drop_index("ix_item_suppliers_item_id", table_name="item_suppliers")
    op.drop_table("item_suppliers")

    op.drop_index("ix_item_reviews_item_rating", table_name="item_reviews")
    op.drop_index("ix_item_reviews_item_id", table_name="item_reviews")
    op.drop_table("item_reviews")

    op.drop_index("ix_item_details_sku", table_name="item_details")
    op.drop_index("ix_item_details_item_id", table_name="item_details")
    op.drop_table("item_details")

    op.drop_index("ix_suppliers_name", table_name="suppliers")
    op.drop_table("suppliers")

    op.drop_index("ix_items_rating", table_name="items")
    op.drop_index("ix_items_name", table_name="items")
    op.drop_index("ix_items_inventory_count", table_name="items")
    op.drop_index("ix_items_deleted_at", table_name="items")
    op.drop_index("ix_items_deleted_active_category", table_name="items")
    op.drop_index("ix_items_created_at", table_name="items")
    op.drop_index("ix_items_category", table_name="items")
    op.drop_index("ix_items_active_category", table_name="items")
    op.drop_table("items")
