"""order item status

Fulfillment status moves from Order (whole order, can span shops) to
OrderItem (per shop line item) — a shop should only control the status of
its own items, not the entire order.

Revision ID: b78dd45fab3c
Revises: 7ef3917f1147
Create Date: 2026-08-06 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = "b78dd45fab3c"
down_revision: Union[str, Sequence[str], None] = "7ef3917f1147"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "order_items",
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index(
        op.f("ix_order_items_status"), "order_items", ["status"], unique=False
    )

    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_column("orders", "status")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "orders",
        sa.Column(
            "status",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default="pending",
        ),
    )
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)

    op.drop_index(op.f("ix_order_items_status"), table_name="order_items")
    op.drop_column("order_items", "status")
