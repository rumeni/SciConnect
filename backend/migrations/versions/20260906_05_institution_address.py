"""A written address for an institution, used to derive its map coordinates.

Revision ID: 20260906_05
Revises: 20260905_04
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260906_05"
down_revision: str | None = "20260905_04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("institutions", sa.Column("address", sa.String(300)))


def downgrade() -> None:
    op.drop_column("institutions", "address")
