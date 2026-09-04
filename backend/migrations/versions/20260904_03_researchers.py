"""Researchers and the analysis-researcher capability link.

Revision ID: 20260904_03
Revises: 20260901_02
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260904_03"
down_revision: str | None = "20260901_02"
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
        "researchers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("title", sa.String(160)),
        sa.Column("email", sa.String(320)),
        sa.Column("orcid", sa.String(40)),
        sa.Column("expertise", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["institution_id"],
            ["institutions.id"],
            name="fk_researchers_institution_id_institutions",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("orcid", name="uq_researchers_orcid"),
        sa.UniqueConstraint("id", "institution_id", name="uq_researcher_same_institution"),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'archived')",
            name="valid_status",
        ),
    )
    op.create_index("ix_researchers_institution", "researchers", ["institution_id"])

    op.create_table(
        "institution_analysis_researchers",
        sa.Column("institution_analysis_id", sa.Integer(), primary_key=True),
        sa.Column("researcher_id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(
            ["institution_analysis_id", "institution_id"],
            ["institution_analyses.id", "institution_analyses.institution_id"],
            name="fk_institution_analysis_researchers_analysis",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["researcher_id", "institution_id"],
            ["researchers.id", "researchers.institution_id"],
            name="fk_institution_analysis_researchers_researcher",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "role IN ('lead', 'contributor', 'contact')",
            name="valid_role",
        ),
    )


def downgrade() -> None:
    op.drop_table("institution_analysis_researchers")
    op.drop_index("ix_researchers_institution", table_name="researchers")
    op.drop_table("researchers")
