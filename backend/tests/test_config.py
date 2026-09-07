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


def test_the_resulting_url_resolves_to_psycopg3() -> None:
    """The actual failure: a driverless URL resolved to the absent psycopg2."""
    assert make_url("postgresql://u:p@h/db").get_dialect().driver == "psycopg2"

    resolved = make_url(_url("postgresql://u:p@h/db")).get_dialect()

    assert resolved.driver == "psycopg"


def test_the_shipped_default_already_names_the_driver() -> None:
    # Read the declared default: the test harness overrides DATABASE_URL.
    default = Settings.model_fields["database_url"].default

    assert default.startswith("postgresql+psycopg://")
