"""blogs: simplify to cover + content (SEO derived from the content)

Revision ID: d5e1b3c8f7a2
Revises: c4d9a27e1b36
Create Date: 2026-10-08 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d5e1b3c8f7a2"
down_revision: Union[str, Sequence[str], None] = "c4d9a27e1b36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Dropping a column also drops its index in Postgres.
DROPPED = (
    "excerpt",
    "tags",
    "meta_title",
    "meta_description",
    "is_published",
    "published_at",
    "reading_minutes",
)


def upgrade() -> None:
    """Upgrade schema."""
    for column in DROPPED:
        op.drop_column("blogs", column)


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("blogs", sa.Column("excerpt", sa.String(length=500), nullable=True))
    op.add_column("blogs", sa.Column("tags", sa.JSON(), nullable=True))
    op.add_column("blogs", sa.Column("meta_title", sa.String(length=191), nullable=True))
    op.add_column("blogs", sa.Column("meta_description", sa.String(length=320), nullable=True))
    op.add_column(
        "blogs",
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("blogs", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.add_column(
        "blogs",
        sa.Column("reading_minutes", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index("ix_blogs_is_published", "blogs", ["is_published"])
    op.create_index("ix_blogs_published_at", "blogs", ["published_at"])
