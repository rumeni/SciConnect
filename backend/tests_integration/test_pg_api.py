"""The API end to end on PostgreSQL: writes, links, search, deletes, constraints.

The SQLite suite covers the behaviour in depth. These tests repeat a
representative path on the production dialect, where constraint enforcement,
column lengths and transaction rollback differ from SQLite.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm import Session

from app.modules.catalog.models import (
    INSTITUTION_SLUG_MAX_LENGTH,
    Institution,
    InstitutionAnalysisInstrument,
    Researcher,
)
from app.seed import seed_catalog


def _create(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(f"/api/v1{path}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _institution(client: TestClient, name: str) -> dict:
    return _create(
        client, "/catalog/institutions", {"name": name, "city": "Belgrade", "country": "Serbia"}
    )


# --- Through the API --------------------------------------------------------


def test_database_readiness_reports_postgres_at_the_migrated_head(client: TestClient) -> None:
    body = client.get("/api/v1/health/database").json()
    assert body["database"] == "ok"
    assert body["driver"] == "psycopg"
    assert body["migration"]
    assert body["institutions"] == 0


def test_a_full_capability_is_created_linked_found_and_unlinked(client: TestClient) -> None:
    institution = _institution(client, "Институт за вирусологију")
    assert institution["slug"] == "institut-za-virusologiju"
    instrument_type = _create(client, "/catalog/instrument-types", {"name": "PCR System"})
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    organism = _create(client, "/catalog/microorganisms", {"scientific_name": "SARS-CoV-2"})
    researcher = _create(
        client,
        "/catalog/researchers",
        {"institution_id": institution["id"], "full_name": "Milica Petrović"},
    )
    instrument = _create(
        client,
        "/catalog/institution-instruments",
        {
            "institution_id": institution["id"],
            "instrument_type_id": instrument_type["id"],
            "display_name": "QuantStudio 7",
        },
    )
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {
            "institution_id": institution["id"],
            "analysis_type_id": analysis_type["id"],
            "public_name": "Respiratory virus RT-PCR",
        },
    )
    analysis_path = f"/institution-analyses/{analysis['id']}"
    _create(client, f"{analysis_path}/instruments", {"institution_instrument_id": instrument["id"]})
    _create(client, f"{analysis_path}/targets", {"microorganism_id": organism["id"]})
    _create(client, f"{analysis_path}/researchers", {"researcher_id": researcher["id"]})

    params = {"microorganism_ids": organism["id"], "researcher_ids": researcher["id"]}
    search = client.get("/api/v1/capabilities/search", params=params).json()
    assert search["total"] == 1
    matched = search["items"][0]["matched_analyses"][0]
    assert [item["full_name"] for item in matched["researchers"]] == ["Milica Petrović"]

    unlinked = client.delete(f"/api/v1{analysis_path}/targets/{organism['id']}")
    assert unlinked.status_code == 200, unlinked.text
    assert client.get("/api/v1/capabilities/search", params=params).json()["total"] == 0


def test_duplicates_are_conflicts_and_leave_the_session_usable(client: TestClient) -> None:
    _institution(client, "Institut Torlak")
    duplicate = client.post(
        "/api/v1/catalog/institutions",
        json={"name": "Institut Torlak", "city": "Nis", "country": "Serbia"},
    )
    assert duplicate.status_code == 409

    _create(client, "/catalog/instrument-types", {"name": "Sequencer"})
    same_name = client.post("/api/v1/catalog/instrument-types", json={"name": "Sequencer"})
    assert same_name.status_code == 409

    # A failed statement aborts a PostgreSQL transaction; the next request must
    # still succeed, which it only does if the failure was rolled back.
    _create(client, "/catalog/instrument-types", {"name": "Mass spectrometer"})
    names = [item["name"] for item in client.get("/api/v1/catalog/instrument-types").json()]
    assert sorted(names) == ["Mass spectrometer", "Sequencer"]


def test_the_same_link_twice_is_a_conflict(client: TestClient) -> None:
    institution = _institution(client, "Link Institute")
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "Culture"})
    organism = _create(client, "/catalog/microorganisms", {"scientific_name": "E. coli"})
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {"institution_id": institution["id"], "analysis_type_id": analysis_type["id"]},
    )
    path = f"/api/v1/institution-analyses/{analysis['id']}/targets"
    assert client.post(path, json={"microorganism_id": organism["id"]}).status_code == 201
    assert client.post(path, json={"microorganism_id": organism["id"]}).status_code == 409


def test_a_maximum_length_cyrillic_name_fits_the_slug_column(client: TestClient) -> None:
    # SQLite ignores VARCHAR lengths; PostgreSQL would reject an overlong slug.
    institution = _institution(client, "Љ" * 200)
    assert len(institution["slug"]) == INSTITUTION_SLUG_MAX_LENGTH


def test_deleting_an_institution_cascades_on_postgres(
    client: TestClient, pg_engine: Engine
) -> None:
    with Session(pg_engine) as session:
        seed_catalog(session)
        session.commit()
    institutions = client.get("/api/v1/catalog/institutions").json()
    target = next(item for item in institutions if item["name"] == "Institute of Virology")

    refused = client.delete(f"/api/v1/catalog/institutions/{target['id']}")
    assert refused.status_code == 409

    removed = client.delete(
        f"/api/v1/catalog/institutions/{target['id']}", params={"cascade": "true"}
    )
    assert removed.status_code == 200, removed.text
    assert client.get(f"/api/v1/catalog/institutions/{target['id']}").status_code == 404
    with pg_engine.connect() as connection:
        orphans = connection.execute(
            text("SELECT count(*) FROM researchers WHERE institution_id = :id"),
            {"id": target["id"]},
        ).scalar_one()
    assert orphans == 0


def test_a_catalog_type_still_in_use_cannot_be_deleted(client: TestClient) -> None:
    institution = _institution(client, "Instrument Owner")
    instrument_type = _create(client, "/catalog/instrument-types", {"name": "Flow cytometer"})
    _create(
        client,
        "/catalog/institution-instruments",
        {"institution_id": institution["id"], "instrument_type_id": instrument_type["id"]},
    )
    response = client.delete(f"/api/v1/catalog/instrument-types/{instrument_type['id']}")
    assert response.status_code == 409


# --- Constraints enforced by PostgreSQL itself -------------------------------


def _insert_institution(connection, slug: str) -> int:
    return connection.execute(
        insert(Institution)
        .values(name=slug, slug=slug, city="Nis", country="Serbia")
        .returning(Institution.id)
    ).scalar_one()


@pytest.mark.usefixtures("clean_tables")
def test_postgres_rejects_a_researcher_of_a_missing_institution(pg_engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="ForeignKeyViolation"):
        with pg_engine.begin() as connection:
            connection.execute(insert(Researcher).values(institution_id=999_999, full_name="X"))


@pytest.mark.usefixtures("clean_tables")
def test_postgres_rejects_a_duplicate_slug(pg_engine: Engine) -> None:
    with pg_engine.begin() as connection:
        _insert_institution(connection, "taken")
    with pytest.raises(IntegrityError, match="UniqueViolation"):
        with pg_engine.begin() as connection:
            _insert_institution(connection, "taken")


@pytest.mark.usefixtures("clean_tables")
def test_postgres_rejects_a_slug_longer_than_the_column(pg_engine: Engine) -> None:
    with pytest.raises(DataError, match="StringDataRightTruncation"):
        with pg_engine.begin() as connection:
            _insert_institution(connection, "x" * (INSTITUTION_SLUG_MAX_LENGTH + 1))


@pytest.mark.usefixtures("clean_tables")
def test_postgres_rejects_an_invalid_status(pg_engine: Engine) -> None:
    with pytest.raises(IntegrityError, match="CheckViolation"):
        with pg_engine.begin() as connection:
            connection.execute(
                insert(Institution).values(
                    name="Bad", slug="bad", city="Nis", country="Serbia", status="deleted"
                )
            )


def test_postgres_rejects_linking_another_institutions_instrument(client: TestClient) -> None:
    """The composite foreign key keeps an analysis and its instrument together."""
    owner = _institution(client, "Owner")
    outsider = _institution(client, "Outsider")
    instrument_type = _create(client, "/catalog/instrument-types", {"name": "Microscope"})
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "Imaging"})
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {"institution_id": owner["id"], "analysis_type_id": analysis_type["id"]},
    )
    foreign_instrument = _create(
        client,
        "/catalog/institution-instruments",
        {"institution_id": outsider["id"], "instrument_type_id": instrument_type["id"]},
    )

    from app.core.database import engine

    with pytest.raises(IntegrityError, match="ForeignKeyViolation"):
        with engine.begin() as connection:
            connection.execute(
                insert(InstitutionAnalysisInstrument).values(
                    institution_analysis_id=analysis["id"],
                    institution_instrument_id=foreign_instrument["id"],
                    institution_id=owner["id"],
                )
            )
