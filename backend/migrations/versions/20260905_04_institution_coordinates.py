"""Optional map coordinates for an institution.

Revision ID: 20260905_04
Revises: 20260904_03
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260905_04"
down_revision: str | None = "20260904_03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("institutions", sa.Column("latitude", sa.Float()))
    op.add_column("institutions", sa.Column("longitude", sa.Float()))
    op.create_check_constraint(
        "coordinates_are_paired", "institutions", "(latitude IS NULL) = (longitude IS NULL)"
    )
    op.create_check_constraint(
        "latitude_in_range", "institutions", "latitude IS NULL OR latitude BETWEEN -90 AND 90"
    )
    op.create_check_constraint(
        "longitude_in_range",
        "institutions",
        "longitude IS NULL OR longitude BETWEEN -180 AND 180",
    )


def downgrade() -> None:
    # op.f() marks these as finished names: without it the naming convention
    # prefixes them a second time and the rollback drops constraints that do
    # not exist.
    op.drop_constraint(
        op.f("ck_institutions_longitude_in_range"), "institutions", type_="check"
    )
    op.drop_constraint(
        op.f("ck_institutions_latitude_in_range"), "institutions", type_="check"
    )
    op.drop_constraint(
        op.f("ck_institutions_coordinates_are_paired"), "institutions", type_="check"
    )
    op.drop_column("institutions", "longitude")
    op.drop_column("institutions", "latitude")
