"""add video url to products

Revision ID: 18f9b5b6fffd
Revises: 2a8989ffb3bc
Create Date: 2026-09-01 18:10:17.791594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18f9b5b6fffd'
down_revision: Union[str, Sequence[str], None] = '2a8989ffb3bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products", sa.Column("video_url", sa.String(length=500), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("products", "video_url")
