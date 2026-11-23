"""Alembic migrations, applied to a real PostgreSQL 17 database.

The container entrypoint runs `alembic upgrade head` on every start, so a
migration that only fails on PostgreSQL would otherwise first fail in
production.
"""

from collections.abc import Iterator

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.core.database import Base
from app.modules.catalog import models  # noqa: F401
from tests_integration.conftest import (
    _scratch_name,
    alembic_config,
    create_database,
    downgrade,
    drop_database,
    upgrade,
)


def _head() -> str:
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    assert len(heads) == 1, f"migrations have {len(heads)} heads: {heads}"
    return heads[0]


def _current(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def test_an_empty_database_migrates_to_the_single_head(pg_engine: Engine) -> None:
    assert _current(pg_engine) == _head()


def test_the_migrated_schema_matches_the_models(pg_engine: Engine) -> None:
    # The same check as `alembic check`: autogenerate finds nothing to add.
    with pg_engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={"compare_type": True})
        differences = compare_metadata(context, Base.metadata)
    assert differences == []


def test_the_postgres_server_is_version_17(pg_engine: Engine) -> None:
    with pg_engine.connect() as connection:
        version = connection.execute(text("SHOW server_version_num")).scalar_one()
    assert int(version) // 10000 == 17, f"expected PostgreSQL 17, got {version}"


@pytest.fixture
def scratch_url() -> Iterator[URL]:
    """A second, empty database for tests that move the schema up and down."""
    name = _scratch_name("sciconnect_mig")
    url = create_database(name)
    try:
        yield url
    finally:
        drop_database(name)


def test_migrations_downgrade_to_base_and_upgrade_again(scratch_url: URL) -> None:
    engine = create_engine(scratch_url)
    try:
        upgrade(scratch_url)
        assert _current(engine) == _head()

        downgrade(scratch_url, "base")
        assert _current(engine) is None
        assert set(inspect(engine).get_table_names()) == {"alembic_version"}

        upgrade(scratch_url)
        assert _current(engine) == _head()
    finally:
        engine.dispose()


def test_every_revision_applies_one_step_at_a_time(scratch_url: URL) -> None:
    script = ScriptDirectory.from_config(alembic_config())
    revisions = [revision.revision for revision in script.walk_revisions("base", "heads")]
    engine = create_engine(scratch_url)
    try:
        for revision in reversed(revisions):
            upgrade(scratch_url, revision)
            assert _current(engine) == revision
    finally:
        engine.dispose()
