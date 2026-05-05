"""add auto increment order number default

Revision ID: 2e2d2314f04a
Revises: e6b866ba74b7
Create Date: 2026-05-05 15:46:32.648688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2e2d2314f04a'
down_revision: Union[str, Sequence[str], None] = 'e6b866ba74b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE SEQUENCE IF NOT EXISTS order_number_seq")
    op.execute(
        """
        SELECT setval(
            'order_number_seq',
            COALESCE(
                (
                    SELECT MAX(order_number::bigint)
                    FROM orders
                    WHERE order_number ~ '^[0-9]+$'
                ),
                0
            ) + 1,
            false
        )
        """
    )
    op.execute(
        "UPDATE orders "
        "SET order_number = nextval('order_number_seq')::text "
        "WHERE order_number IS NULL"
    )
    op.alter_column(
        "orders",
        "order_number",
        existing_type=sa.String(),
        nullable=False,
        server_default=sa.text("nextval('order_number_seq')::text"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "orders",
        "order_number",
        existing_type=sa.String(),
        nullable=True,
        server_default=None,
    )
    op.execute("DROP SEQUENCE IF EXISTS order_number_seq")
