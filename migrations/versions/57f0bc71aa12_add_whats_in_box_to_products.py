"""add whats in box to products

Revision ID: 57f0bc71aa12
Revises: 18f9b5b6fffd
Create Date: 2026-09-08 12:35:36.470135

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57f0bc71aa12'
down_revision: Union[str, Sequence[str], None] = '18f9b5b6fffd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("products", sa.Column("whats_in_box", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "whats_in_box")
