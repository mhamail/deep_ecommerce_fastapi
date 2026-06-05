"""merge order items into orders

Revision ID: 4e3d1a2b9c0f
Revises: e01ee34a6422
Create Date: 2026-06-05 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "4e3d1a2b9c0f"
down_revision: Union[str, Sequence[str], None] = "e01ee34a6422"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "orders",
        sa.Column(
            "items",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
    )

    op.execute(
        """
        UPDATE orders AS orders_table
        SET items = order_item_snapshots.items
        FROM (
            SELECT
                order_id,
                json_agg(
                    json_build_object(
                        'product_id', product_id,
                        'product_variant_id', product_variant_id,
                        'product_name', product_name,
                        'variant_attributes', variant_attributes,
                        'price', price,
                        'quantity', quantity,
                        'image', image,
                        'line_total', price * quantity
                    )
                    ORDER BY id
                ) AS items
            FROM order_items
            GROUP BY order_id
        ) AS order_item_snapshots
        WHERE orders_table.id = order_item_snapshots.order_id
        """
    )

    op.drop_table("order_items")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "order_items",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("product_variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("variant_attributes", sa.JSON(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("image", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.ForeignKeyConstraint(["product_variant_id"], ["product_variants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_order_items_order_id"), "order_items", ["order_id"], unique=False
    )
    op.create_index(
        op.f("ix_order_items_product_id"), "order_items", ["product_id"], unique=False
    )

    op.execute(
        """
        INSERT INTO order_items (
            created_at,
            updated_at,
            order_id,
            product_id,
            product_variant_id,
            product_name,
            variant_attributes,
            price,
            quantity,
            image
        )
        SELECT
            orders_table.created_at,
            orders_table.updated_at,
            orders_table.id,
            (item ->> 'product_id')::integer,
            (item ->> 'product_variant_id')::integer,
            item ->> 'product_name',
            item -> 'variant_attributes',
            (item ->> 'price')::double precision,
            (item ->> 'quantity')::integer,
            item -> 'image'
        FROM orders AS orders_table
        CROSS JOIN LATERAL json_array_elements(orders_table.items) AS item
        """
    )

    op.drop_column("orders", "items")
