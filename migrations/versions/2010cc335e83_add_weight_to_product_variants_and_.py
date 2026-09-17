"""add weight to product_variants and order_items

Revision ID: 2010cc335e83
Revises: e9cf4b4ab33c
Create Date: 2026-09-17 11:23:13.847971

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2010cc335e83'
down_revision: Union[str, Sequence[str], None] = 'e9cf4b4ab33c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("product_variants", sa.Column("weight", sa.Float(), nullable=True))
    op.add_column("order_items", sa.Column("weight", sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("order_items", "weight")
    op.drop_column("product_variants", "weight")
