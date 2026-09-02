"""Normalize check constraint names created by the first development migration.

Revision ID: 20260901_02
Revises: 20260831_01
Create Date: 2026-09-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260901_02"
down_revision: str | None = "20260831_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


RENAMES = [
    (
        "institutions",
        "ck_institutions_ck_institutions_valid_status",
        "ck_institutions_valid_status",
    ),
    (
        "institution_instruments",
        "ck_institution_instruments_ck_institution_instruments_v_7ef4",
        "ck_institution_instruments_valid_status",
    ),
    (
        "institution_analyses",
        "ck_institution_analyses_ck_institution_analyses_positive_days",
        "ck_institution_analyses_positive_days",
    ),
    (
        "institution_analyses",
        "ck_institution_analyses_ck_institution_analyses_valid_a_7fc5",
        "ck_institution_analyses_valid_availability",
    ),
    (
        "institution_analysis_instruments",
        "ck_institution_analysis_instruments_ck_institution_anal_754f",
        "ck_institution_analysis_instruments_valid_usage",
    ),
]


def _rename_if_present(table: str, old_name: str, new_name: str) -> None:
    op.execute(
        f"""
        DO $migration$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = '{old_name}'
                  AND conrelid = '{table}'::regclass
            ) THEN
                ALTER TABLE {table} RENAME CONSTRAINT {old_name} TO {new_name};
            END IF;
        END
        $migration$;
        """
    )


def upgrade() -> None:
    for table, old_name, new_name in RENAMES:
        _rename_if_present(table, old_name, new_name)


def downgrade() -> None:
    # This is a compatibility migration for an early development database.
    # Reverting names would make a clean database disagree with model metadata.
    pass
