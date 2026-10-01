"""Cases a code review found that the rest of the suite walked past.

They share a shape: something outside the application's control — a generated
password, a concurrent writer, a third-party response, a catalogue larger than
the demo data — reaching code that assumed it would be well behaved.
"""

import httpx
import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.modules.catalog import geocoding
from app.modules.catalog.lookup import find_entities
from app.modules.catalog.models import InstrumentType

# --- The database URL reaches Alembic intact -------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://user:example%40password@host:5432/db",
        "postgresql+psycopg://user:100%25secret@host:5432/db",
        "postgresql+psycopg://user:plain@host:5432/db",
    ],
    ids=["encoded @", "encoded %", "no escaping needed"],
)
def test_a_percent_encoded_password_survives_alembic_configuration(url: str) -> None:
    """Alembic reads this through configparser, which treats % as interpolation."""
    config = Config()

    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))

    assert config.get_main_option("sqlalchemy.url") == url


# --- A constraint the pre-check cannot cover is still the caller's fault ----


def _institution(client: TestClient) -> int:
    return client.post(
        "/api/v1/catalog/institutions",
        json={"name": "Holder", "city": "Nis", "country": "Serbia"},
    ).json()["id"]


def test_a_blank_orcid_is_stored_as_absent(client: TestClient) -> None:
    """Two blank ORCIDs are two identical values; two absent ones are unrelated."""
    institution_id = _institution(client)
    payload = {"institution_id": institution_id, "orcid": ""}

    first = client.post(
        "/api/v1/catalog/researchers", json={**payload, "full_name": "First Person"}
    )
    second = client.post(
        "/api/v1/catalog/researchers", json={**payload, "full_name": "Second Person"}
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["orcid"] is None


def test_a_duplicate_orcid_is_refused_rather_than_crashing(client: TestClient) -> None:
    institution_id = _institution(client)
    payload = {"institution_id": institution_id, "orcid": "0000-0002-1825-0097"}

    client.post("/api/v1/catalog/researchers", json={**payload, "full_name": "A"})
    second = client.post("/api/v1/catalog/researchers", json={**payload, "full_name": "B"})

    assert second.status_code == 409


def test_the_session_still_works_after_a_refused_write(client: TestClient) -> None:
    """A rejected write must not poison the session for the next request."""
    institution_id = _institution(client)
    payload = {"institution_id": institution_id, "orcid": "0000-0002-1825-0097"}
    client.post("/api/v1/catalog/researchers", json={**payload, "full_name": "A"})
    client.post("/api/v1/catalog/researchers", json={**payload, "full_name": "B"})

    after = client.post(
        "/api/v1/catalog/researchers",
        json={"institution_id": institution_id, "full_name": "C"},
    )

    assert after.status_code == 201


# --- The geocoder's answer is never trusted --------------------------------


def _geocode(payload: object) -> geocoding.Location | None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    original = httpx.get

    def patched(url, **kwargs):
        with httpx.Client(transport=transport) as stub:
            return stub.get(url, **kwargs)

    httpx.get = patched
    try:
        return geocoding.nominatim_geocoder("anywhere")
    finally:
        httpx.get = original


@pytest.mark.parametrize(
    "payload",
    [
        {"error": "Unable to geocode"},
        "not json at all",
        [],
        [{"lon": "20.4"}],
        [{"lat": "not-a-number", "lon": "20.4"}],
        [{"lat": "100", "lon": "20.4"}],
        [{"lat": "44.8", "lon": "999"}],
        [{"lat": "NaN", "lon": "20.4"}],
    ],
    ids=[
        "error object",
        "a bare string",
        "no matches",
        "missing latitude",
        "unparseable latitude",
        "latitude past the pole",
        "longitude off the globe",
        "not a number at all",
    ],
)
def test_an_unusable_geocoding_answer_yields_no_location(payload: object) -> None:
    assert _geocode(payload) is None


def test_a_usable_answer_still_works() -> None:
    located = _geocode([{"lat": "44.8", "lon": "20.4", "display_name": "Belgrade"}])

    assert located == geocoding.Location(44.8, 20.4, "Belgrade")


def test_an_unplaceable_address_still_creates_the_institution(
    client: TestClient, use_geocoder
) -> None:
    """The whole point of the above: a bad reply must not fail the write."""
    use_geocoder(None)

    response = client.post(
        "/api/v1/catalog/institutions",
        json={"name": "Unplaceable", "city": "Nowhere", "country": "Atlantis"},
    )

    assert response.status_code == 201
    assert response.json()["latitude"] is None


# --- Search ranks before it cuts -------------------------------------------


@pytest.fixture
def crowded() -> Session:
    """More matches of one kind than the answer can hold."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        # The exact match sorts last alphabetically, so an alphabetical cut loses it.
        for index in range(23):
            session.add(InstrumentType(name=f"Advanced scope model {index:02d}"))
        session.add(InstrumentType(name="Scope"))
        session.flush()
        yield session


def test_the_best_match_survives_the_limit(crowded: Session) -> None:
    answer = find_entities(crowded, "Scope", limit=20)

    assert [match.label for match in answer.items][0] == "Scope"


def test_a_kind_cut_short_reports_truncation(crowded: Session) -> None:
    answer = find_entities(crowded, "Scope", limit=20)

    assert len(answer.items) == 20
    assert answer.truncated is True


def test_an_answer_that_fits_is_not_reported_as_truncated(crowded: Session) -> None:
    answer = find_entities(crowded, "Scope", limit=50)

    assert len(answer.items) == 24
    assert answer.truncated is False
