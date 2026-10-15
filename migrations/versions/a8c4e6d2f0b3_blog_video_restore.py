"""blog video resolved again

Undoes f7a3d5b9c2e1: the blog's `video_url` is resolved on save again
(YouTube / Vimeo title + thumbnail), so the `video` JSON column is back.
The resolved details can't be rebuilt here (that needs network calls), so
re-save a post with its video link to fill `video` in; the old plain links
are dropped with the `video_url` column.

Revision ID: a8c4e6d2f0b3
Revises: f7a3d5b9c2e1
Create Date: 2026-10-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a8c4e6d2f0b3"
down_revision: Union[str, Sequence[str], None] = "f7a3d5b9c2e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("blogs", sa.Column("video", sa.JSON(), nullable=True))
    op.drop_column("blogs", "video_url")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("blogs", sa.Column("video_url", sa.String(length=500), nullable=True))
    op.drop_column("blogs", "video")
