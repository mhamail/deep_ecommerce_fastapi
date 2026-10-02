"""home sections and banners

Revision ID: a7c1f3d92b10
Revises: 2010cc335e83
Create Date: 2026-10-02 10:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c1f3d92b10"
down_revision: Union[str, Sequence[str], None] = "2010cc335e83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    sections = op.create_table(
        "home_sections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=191), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("full_width", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("columns", sa.Integer(), nullable=True),
        sa.Column("autoplay", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("product_limit", sa.Integer(), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_home_sections_type", "home_sections", ["type"])
    op.create_index("ix_home_sections_position", "home_sections", ["position"])
    op.create_index("ix_home_sections_is_active", "home_sections", ["is_active"])
    op.create_index("ix_home_sections_category_id", "home_sections", ["category_id"])

    op.create_table(
        "banners",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "section_id",
            sa.Integer(),
            sa.ForeignKey("home_sections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("image", sa.JSON(), nullable=True),
        sa.Column("title", sa.String(length=191), nullable=True),
        sa.Column("content", sa.String(), nullable=True),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column("open_in_new_tab", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_banners_section_id", "banners", ["section_id"])
    op.create_index("ix_banners_position", "banners", ["position"])
    op.create_index("ix_banners_is_active", "banners", ["is_active"])

    # Seed the three blocks the storefront homepage hard-coded before this
    # existed, so deploying the migration changes nothing visible until an
    # admin edits the layout.
    # A Python value, not sa.func.now(): bulk_insert binds rows as executemany
    # parameters, and psycopg2 can't adapt a SQL expression.
    now = datetime.utcnow()
    op.bulk_insert(
        sections,
        [
            {"type": "hero", "title": None, "position": 0, "product_limit": 6, "created_at": now},
            {"type": "featured_products", "title": "Exclusive Products", "position": 1, "product_limit": 8, "created_at": now},
            {"type": "product_list", "title": "Shop Products", "position": 2, "product_limit": 12, "created_at": now},
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("banners")
    op.drop_table("home_sections")
