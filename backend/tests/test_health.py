from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.main import app
from app.seed import seed_catalog


def test_liveness_does_not_need_the_database(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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
    assert body["institutions"] == 5


def test_a_reachable_but_unmigrated_database_is_told_apart(client: TestClient) -> None:
    """No alembic_version table, yet the connection itself is fine."""
    body = client.get("/api/v1/health/database").json()

    assert body["database"] == "ok"
    assert body["migration"] is None


def test_an_unreachable_database_answers_503(client: TestClient) -> None:
    class Unreachable:
        def execute(self, *_args: object, **_kwargs: object) -> None:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

        def rollback(self) -> None:
            pass

    app.dependency_overrides[get_db] = lambda: Unreachable()
    try:
        response = client.get("/api/v1/health/database")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    body = response.json()
    assert body["database"] == "unavailable"
    assert body["error"] == "OperationalError"


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
