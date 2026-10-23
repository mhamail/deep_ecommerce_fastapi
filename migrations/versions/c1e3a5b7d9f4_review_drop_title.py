"""drop product review title

Reviews are a rating + one comment box; the separate title is gone.

Revision ID: c1e3a5b7d9f4
Revises: b9d1f3a5c7e2
Create Date: 2026-10-23 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1e3a5b7d9f4"
down_revision: Union[str, Sequence[str], None] = "b9d1f3a5c7e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("product_reviews", "title")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "product_reviews", sa.Column("title", sa.String(length=120), nullable=True)
    )
