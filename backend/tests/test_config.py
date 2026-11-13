import pytest
from sqlalchemy.engine.url import make_url

from app.core.config import Settings


def _url(value: str) -> str:
    return Settings(database_url=value).database_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # What a managed host such as Render injects.
        (
            "postgresql://user:pass@host:5432/sciconnect",
            "postgresql+psycopg://user:pass@host:5432/sciconnect",
        ),
        # The legacy Heroku-style scheme, which SQLAlchemy cannot read at all.
        (
            "postgres://user:pass@host:5432/sciconnect",
            "postgresql+psycopg://user:pass@host:5432/sciconnect",
        ),
    ],
)
def test_a_driverless_postgres_url_names_the_installed_driver(
    given: str, expected: str
) -> None:
    assert _url(given) == expected


def test_query_parameters_survive_the_rewrite() -> None:
    """Hosts append options such as sslmode; losing them would break TLS."""
    given = "postgresql://user:pass@host:5432/sciconnect?sslmode=require"

    assert _url(given).endswith("@host:5432/sciconnect?sslmode=require")
    assert make_url(_url(given)).query["sslmode"] == "require"


@pytest.mark.parametrize(
    "given",
    [
        "postgresql+psycopg://user:pass@host:5432/sciconnect",
        "postgresql+asyncpg://user:pass@host:5432/sciconnect",
        "sqlite+pysqlite:///:memory:",
    ],
)
def test_an_explicit_driver_is_left_alone(given: str) -> None:
    assert _url(given) == given


@pytest.mark.parametrize("given", ["postgresql://u:p@h/db", "postgres://u:p@h/db"])
def test_the_resulting_url_resolves_to_psycopg3(given: str) -> None:
    """A driverless URL must end up on psycopg 3, the only driver installed.

    SQLAlchemy's own default for a driverless URL changed between releases
    (psycopg2 in 2.0, psycopg in 2.1), so this checks only the rewritten URL:
    it names the driver itself and does not depend on that default.
    """
    resolved = make_url(_url(given)).get_dialect()

    assert resolved.driver == "psycopg"


def test_the_shipped_default_already_names_the_driver() -> None:
    # Read the declared default: the test harness overrides DATABASE_URL.
    default = Settings.model_fields["database_url"].default

    assert default.startswith("postgresql+psycopg://")
