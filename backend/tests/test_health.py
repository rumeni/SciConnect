import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.seed import INSTITUTIONS, seed_catalog


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_liveness_does_not_need_the_database(client: TestClient, method: str) -> None:
    def unavailable_database():
        raise AssertionError("Liveness must not acquire a database session")

    app.dependency_overrides[get_db] = unavailable_database
    response = client.request(method, "/api/v1/health")

    assert response.status_code == 200
    if method == "GET":
        assert response.json() == {"status": "ok"}
    else:
        assert response.content == b""


def test_head_readiness_checks_the_database_without_a_body(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    statements: list[str] = []
    execute = db.execute

    def record_execute(statement, *args, **kwargs):
        statements.append(str(statement))
        return execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", record_execute)
    response = client.head("/api/v1/health/database")

    assert response.status_code == 200
    assert response.content == b""
    assert "SELECT 1" in statements


def test_readiness_reports_a_reachable_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/database")

    assert response.status_code == 200
    body = response.json()
    assert body["database"] == "ok"
    assert body["institutions"] == 0


def test_readiness_counts_what_the_database_holds(
    client: TestClient, db: Session
) -> None:
    seed_catalog(db)
    db.commit()

    body = client.get("/api/v1/health/database").json()

    assert body["database"] == "ok"
    assert body["institutions"] == len(INSTITUTIONS)


def test_a_reachable_but_unmigrated_database_is_told_apart(client: TestClient) -> None:
    """No alembic_version table, yet the connection itself is fine."""
    body = client.get("/api/v1/health/database").json()

    assert body["database"] == "ok"
    assert body["migration"] is None


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_an_unreachable_database_answers_503(client: TestClient, method: str) -> None:
    class Unreachable:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        def rollback(self) -> None:
            pass

    app.dependency_overrides[get_db] = lambda: Unreachable()
    try:
        response = client.request(method, "/api/v1/health/database")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    if method == "GET":
        body = response.json()
        assert body["database"] == "unavailable"
        assert body["error"] == "OperationalError"
    else:
        assert response.content == b""


def test_the_failure_reply_carries_no_connection_details(client: TestClient) -> None:
    """The endpoint is public, so host and user names must stay in the logs."""

    class Unreachable:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OperationalError(
                "SELECT 1",
                {},
                Exception('connection to server at "10.0.0.4", port 5432 failed'),
            )

        def rollback(self) -> None:
            pass

    app.dependency_overrides[get_db] = lambda: Unreachable()
    try:
        text_body = client.get("/api/v1/health/database").text
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert "10.0.0.4" not in text_body
    assert "5432" not in text_body
