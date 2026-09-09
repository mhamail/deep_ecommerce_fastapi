"""add short description to products

Revision ID: 610a2bba72ef
Revises: 57f0bc71aa12
Create Date: 2026-09-09 15:14:57.271431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '610a2bba72ef'
down_revision: Union[str, Sequence[str], None] = '57f0bc71aa12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products", sa.Column("short_description", sa.String(length=300), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "short_description")
