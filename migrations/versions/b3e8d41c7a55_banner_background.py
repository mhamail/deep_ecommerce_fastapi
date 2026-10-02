"""banner background

Revision ID: b3e8d41c7a55
Revises: a7c1f3d92b10
Create Date: 2026-10-02 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3e8d41c7a55"
down_revision: Union[str, Sequence[str], None] = "a7c1f3d92b10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("banners", sa.Column("background", sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("banners", "background")
