"""blog video link

Revision ID: e6f2c4a9d1b8
Revises: d5e1b3c8f7a2
Create Date: 2026-10-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6f2c4a9d1b8"
down_revision: Union[str, Sequence[str], None] = "d5e1b3c8f7a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("blogs", sa.Column("video", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("blogs", "video")
