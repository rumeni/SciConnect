"""Fixtures for the PostgreSQL integration suite.

These tests run against a real PostgreSQL server, never the SQLite fixtures in
`tests/`. Point INTEGRATION_DATABASE_URL at a server you can create databases
on, for example the one in compose.yaml or a throwaway container:

    docker run --rm -d -p 5433:5432 -e POSTGRES_PASSWORD=postgres postgres:17-alpine
    INTEGRATION_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/postgres \
        python -m pytest tests_integration

The suite creates its own uniquely named database on that server, migrates it
with Alembic from empty, and drops it again at the end, so it never touches an
existing database and two runs (or two xdist workers) cannot collide. Without
INTEGRATION_DATABASE_URL every test here is skipped.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import URL, create_engine, make_url, text
from sqlalchemy.engine import Engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
SERVER_URL_VARIABLE = "INTEGRATION_DATABASE_URL"
# Only a database on this machine (or a CI service container reached through
# localhost) may be used. This keeps a stray production URL in someone's
# environment from ever being created on, migrated or dropped.
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _server_url() -> URL | None:
    raw = os.environ.get(SERVER_URL_VARIABLE)
    if not raw:
        return None
    url = make_url(raw)
    if url.get_backend_name() != "postgresql":
        raise pytest.UsageError(f"{SERVER_URL_VARIABLE} must be a PostgreSQL URL")
    if url.host not in LOCAL_HOSTS:
        raise pytest.UsageError(
            f"{SERVER_URL_VARIABLE} must point at a local server "
            f"({', '.join(sorted(LOCAL_HOSTS))}), not {url.host!r}: "
            "this suite creates and drops databases"
        )
    return url.set(drivername="postgresql+psycopg")


def _scratch_name(prefix: str) -> str:
    worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
    return f"{prefix}_{worker}_{uuid.uuid4().hex[:12]}"


SERVER_URL = _server_url()
DATABASE_NAME = _scratch_name("sciconnect_it")

# The app reads its database URL once, at import. Setting it here, before any
# test module imports `app`, points the real engine, the Alembic env and the
# health probes at the scratch database instead of the development default.
if SERVER_URL is not None:
    os.environ["DATABASE_URL"] = SERVER_URL.set(database=DATABASE_NAME).render_as_string(
        hide_password=False
    )
os.environ.setdefault("APP_RATE_LIMIT_ENABLED", "false")


def pytest_collection_modifyitems(config, items) -> None:
    if SERVER_URL is not None:
        return
    skip = pytest.mark.skip(reason=f"{SERVER_URL_VARIABLE} is not set")
    for item in items:
        item.add_marker(skip)


def create_database(name: str) -> URL:
    assert SERVER_URL is not None
    admin = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        admin.dispose()
    return SERVER_URL.set(database=name)


def drop_database(name: str) -> None:
    assert SERVER_URL is not None
    admin = create_engine(SERVER_URL, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        admin.dispose()


def alembic_config():
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return config


def upgrade(url: URL, revision: str = "head") -> None:
    """Run `alembic upgrade` the way the container entrypoint does."""
    _run_alembic("upgrade", url, revision)


def downgrade(url: URL, revision: str) -> None:
    _run_alembic("downgrade", url, revision)


def _run_alembic(action: str, url: URL, revision: str) -> None:
    from alembic import command

    from app.core.config import settings

    # migrations/env.py reads settings.database_url each time it runs.
    previous = settings.database_url
    settings.database_url = url.render_as_string(hide_password=False)
    try:
        getattr(command, action)(alembic_config(), revision)
    finally:
        settings.database_url = previous


@pytest.fixture(scope="session")
def migrated_url() -> Iterator[URL]:
    """The session's scratch database, migrated from empty to head."""
    if SERVER_URL is None:
        pytest.skip(f"{SERVER_URL_VARIABLE} is not set")
    url = create_database(DATABASE_NAME)
    try:
        upgrade(url)
        yield url
    finally:
        from app.core.database import engine as app_engine

        app_engine.dispose()
        drop_database(DATABASE_NAME)


@pytest.fixture(scope="session")
def pg_engine(migrated_url: URL) -> Iterator[Engine]:
    engine = create_engine(migrated_url)
    yield engine
    engine.dispose()


@pytest.fixture
def clean_tables(pg_engine: Engine) -> Iterator[None]:
    """Empty every application table after the test, keeping the schema."""
    yield
    from app.core.database import Base
    from app.modules.catalog import models  # noqa: F401

    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(pg_engine: Engine, clean_tables: None):
    """The real app, with its own engine and sessions, on the scratch database.

    Unlike the SQLite suite nothing overrides get_db: requests go through the
    same session factory and transaction handling as in production.
    """
    from fastapi.testclient import TestClient

    from app.main import app
    from app.modules.catalog.geocoding import default_geocoder, no_geocoder

    app.dependency_overrides[default_geocoder] = lambda: no_geocoder
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
