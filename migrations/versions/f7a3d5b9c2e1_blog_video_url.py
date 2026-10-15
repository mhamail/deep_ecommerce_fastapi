"""blog video as a plain link

Replaces the resolved `video` JSON (provider / thumbnail / …) with a plain
`video_url` string, keeping the link of any existing post.

Revision ID: f7a3d5b9c2e1
Revises: e6f2c4a9d1b8
Create Date: 2026-10-14 12:00:00.000000

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f7a3d5b9c2e1"
down_revision: Union[str, Sequence[str], None] = "e6f2c4a9d1b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("blogs", sa.Column("video_url", sa.String(length=500), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, video FROM blogs WHERE video IS NOT NULL")
    ).fetchall()
    for blog_id, video in rows:
        if isinstance(video, str):
            video = json.loads(video)
        url = (video or {}).get("url")
        if url:
            conn.execute(
                sa.text("UPDATE blogs SET video_url = :url WHERE id = :id"),
                {"url": url[:500], "id": blog_id},
            )

    op.drop_column("blogs", "video")


def downgrade() -> None:
    """Downgrade schema (the resolved video details can't be restored)."""
    op.add_column("blogs", sa.Column("video", sa.JSON(), nullable=True))
    op.drop_column("blogs", "video_url")
