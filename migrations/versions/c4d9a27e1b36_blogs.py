"""blogs

Revision ID: c4d9a27e1b36
Revises: b3e8d41c7a55
Create Date: 2026-10-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4d9a27e1b36"
down_revision: Union[str, Sequence[str], None] = "b3e8d41c7a55"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "blogs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=191), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=False),
        sa.Column("excerpt", sa.String(length=500), nullable=True),
        sa.Column("content", sa.String(), nullable=False, server_default=""),
        sa.Column("cover_image", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("meta_title", sa.String(length=191), nullable=True),
        sa.Column("meta_description", sa.String(length=320), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("reading_minutes", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_blogs_slug", "blogs", ["slug"], unique=True)
    op.create_index("ix_blogs_is_published", "blogs", ["is_published"])
    op.create_index("ix_blogs_published_at", "blogs", ["published_at"])
    op.create_index("ix_blogs_author_id", "blogs", ["author_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("blogs")
