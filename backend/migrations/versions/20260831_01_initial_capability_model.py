"""Initial capability model.

Revision ID: 20260831_01
Revises:
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_01"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(220), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("country", sa.String(120), nullable=False),
        sa.Column("website", sa.String(500)),
        sa.Column("contact_email", sa.String(320)),
        sa.Column("status", sa.String(20), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')", name="valid_status"
        ),
        sa.UniqueConstraint("slug", name="uq_institutions_slug"),
    )
    op.create_index("ix_institutions_country_city", "institutions", ["country", "city"])

    op.create_table(
        "instrument_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_instrument_types_name"),
    )
    op.create_table(
        "analysis_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_analysis_types_name"),
    )
    op.create_table(
        "microorganisms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scientific_name", sa.String(240), nullable=False),
        sa.Column("common_name", sa.String(240)),
        sa.Column("description", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("scientific_name", name="uq_microorganisms_scientific_name"),
    )

    op.create_table(
        "institution_instruments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("instrument_type_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("manufacturer", sa.String(160)),
        sa.Column("model", sa.String(160)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("access_notes", sa.Text()),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["instrument_type_id"], ["instrument_types.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("id", "institution_id", name="uq_instrument_same_institution"),
        sa.CheckConstraint(
            "status IN ('operational', 'maintenance', 'unavailable', 'archived')",
            name="valid_status",
        ),
    )
    op.create_index(
        "ix_institution_instruments_type",
        "institution_instruments",
        ["instrument_type_id", "institution_id"],
    )

    op.create_table(
        "institution_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("analysis_type_id", sa.Integer(), nullable=False),
        sa.Column("public_name", sa.String(240)),
        sa.Column("description", sa.Text()),
        sa.Column("turnaround_days", sa.Integer()),
        sa.Column("availability", sa.String(20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["analysis_type_id"], ["analysis_types.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint("id", "institution_id", name="uq_analysis_same_institution"),
        sa.UniqueConstraint(
            "institution_id", "analysis_type_id", name="uq_institution_analysis_type"
        ),
        sa.CheckConstraint(
            "turnaround_days IS NULL OR turnaround_days > 0",
            name="positive_days",
        ),
        sa.CheckConstraint(
            "availability IN ('available', 'limited', 'unavailable', 'archived')",
            name="valid_availability",
        ),
    )
    op.create_index(
        "ix_institution_analyses_type",
        "institution_analyses",
        ["analysis_type_id", "institution_id"],
    )

    op.create_table(
        "institution_analysis_instruments",
        sa.Column("institution_analysis_id", sa.Integer(), primary_key=True),
        sa.Column("institution_instrument_id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("usage", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_analysis_id", "institution_id"],
            ["institution_analyses.id", "institution_analyses.institution_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["institution_instrument_id", "institution_id"],
            ["institution_instruments.id", "institution_instruments.institution_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "usage IN ('required', 'optional', 'alternative')",
            name="valid_usage",
        ),
    )

    op.create_table(
        "institution_analysis_targets",
        sa.Column("institution_analysis_id", sa.Integer(), primary_key=True),
        sa.Column("microorganism_id", sa.Integer(), primary_key=True),
        sa.ForeignKeyConstraint(
            ["institution_analysis_id"], ["institution_analyses.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["microorganism_id"], ["microorganisms.id"], ondelete="RESTRICT"
        ),
    )


def downgrade() -> None:
    op.drop_table("institution_analysis_targets")
    op.drop_table("institution_analysis_instruments")
    op.drop_index("ix_institution_analyses_type", table_name="institution_analyses")
    op.drop_table("institution_analyses")
    op.drop_index("ix_institution_instruments_type", table_name="institution_instruments")
    op.drop_table("institution_instruments")
    op.drop_table("microorganisms")
    op.drop_table("analysis_types")
    op.drop_table("instrument_types")
    op.drop_index("ix_institutions_country_city", table_name="institutions")
    op.drop_table("institutions")
