import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
# The suite makes far more requests per minute than a person does, so the
# limits are off unless a test switches them on for itself. `limited` below is
# how a test does that.
os.environ.setdefault("APP_RATE_LIMIT_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.ratelimit import counter as rate_limit_counter
from app.main import app
from app.modules.catalog import models  # noqa: F401
from app.modules.catalog.geocoding import Location, default_geocoder, no_geocoder


@pytest.fixture
def db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record) -> None:
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db: Session) -> TestClient:
    app.dependency_overrides[get_db] = lambda: db
    # No test may reach the real geocoding service. Tests that need a lookup
    # install their own stub with `use_geocoder`.
    app.dependency_overrides[default_geocoder] = lambda: no_geocoder
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def limited(monkeypatch):
    """Switch rate limiting on for one test, with limits it chooses.

    The counters are process-wide, so they are cleared on the way in and on the
    way out: a test that fills a budget must not spend the next test's.
    """

    def configure(**limits: str | int | bool):
        rate_limit_counter.reset()
        monkeypatch.setattr(settings, "rate_limit_enabled", True)
        for name, value in limits.items():
            monkeypatch.setattr(settings, name, value)

    yield configure
    rate_limit_counter.reset()


@pytest.fixture
def admin_token(monkeypatch) -> str:
    """Require a token for writes, and hand the test the one that works."""
    token = "test-admin-token-long-enough-to-be-real-0123456789"
    monkeypatch.setattr(settings, "admin_token", token)
    return token


@pytest.fixture
def use_geocoder():
    """Install a stub address lookup, and record the queries it was asked for."""

    def install(location: Location | None) -> list[str]:
        asked: list[str] = []

        def stub(query: str) -> Location | None:
            asked.append(query)
            return location

        app.dependency_overrides[default_geocoder] = lambda: stub
        return asked

    return install

