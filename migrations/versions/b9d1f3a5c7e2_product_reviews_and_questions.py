"""product reviews, questions and stored rating aggregate

Adds the `product_reviews` / `product_questions` tables and the
`rating_average` / `rating_count` / `rating_breakdown` columns on `products`
(the aggregate product cards read; maintained on every review write).

Revision ID: b9d1f3a5c7e2
Revises: a8c4e6d2f0b3
Create Date: 2026-10-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9d1f3a5c7e2"
down_revision: Union[str, Sequence[str], None] = "a8c4e6d2f0b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column("rating_average", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "products",
        sa.Column("rating_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("products", sa.Column("rating_breakdown", sa.JSON(), nullable=True))

    op.create_table(
        "product_reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=True),
        sa.Column("comment", sa.String(length=2000), nullable=True),
        sa.Column(
            "verified_purchase", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("product_id", "user_id", name="uq_review_product_user"),
        sa.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )
    op.create_index("ix_product_reviews_product_id", "product_reviews", ["product_id"])
    op.create_index("ix_product_reviews_user_id", "product_reviews", ["user_id"])

    op.create_table(
        "product_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.String(length=2000), nullable=True),
        sa.Column(
            "answered_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_product_questions_product_id", "product_questions", ["product_id"]
    )
    op.create_index("ix_product_questions_user_id", "product_questions", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("product_questions")
    op.drop_table("product_reviews")
    op.drop_column("products", "rating_breakdown")
    op.drop_column("products", "rating_count")
    op.drop_column("products", "rating_average")
