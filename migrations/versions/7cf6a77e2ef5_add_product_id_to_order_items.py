"""add product id to order items

Revision ID: 7cf6a77e2ef5
Revises: 7ef668fbbc8c
Create Date: 2026-05-05 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7cf6a77e2ef5"
down_revision: Union[str, Sequence[str], None] = "7ef668fbbc8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("order_items", sa.Column("product_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_order_items_product_id"),
        "order_items",
        ["product_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_order_items_product_id_products",
        "order_items",
        "products",
        ["product_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_order_items_product_id_products",
        "order_items",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_order_items_product_id"), table_name="order_items")
    op.drop_column("order_items", "product_id")
