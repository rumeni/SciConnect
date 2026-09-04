import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed_catalog


@pytest.fixture
def seeded(client: TestClient, db: Session) -> TestClient:
    seed_catalog(db)
    db.commit()
    return client


def _get(client: TestClient, path: str) -> dict:
    response = client.get(f"/api/v1{path}")
    assert response.status_code == 200, response.text
    return response.json()


def _id_of(client: TestClient, path: str, field: str, value: str) -> int:
    for item in _get(client, path):
        if item[field] == value:
            return item["id"]
    raise AssertionError(f"{value} not found in {path}")


def test_institution_detail_lists_everything_it_owns(seeded: TestClient) -> None:
    institution_id = _id_of(
        seeded, "/catalog/institutions", "name", "Institute of Virology"
    )

    body = _get(seeded, f"/catalog/institutions/{institution_id}")

    assert body["city"] == "Belgrade"
    assert body["contact_email"] == "contact.virology@example.org"
    assert len(body["instruments"]) == 2
    assert len(body["analyses"]) == 2
    assert sorted(person["full_name"] for person in body["researchers"]) == [
        "Milica Petrovic",
        "Nikola Ilic",
    ]


def test_researcher_detail_carries_their_institution_and_roles(seeded: TestClient) -> None:
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Nikola Ilic")

    body = _get(seeded, f"/catalog/researchers/{researcher_id}")

    assert body["institution"]["name"] == "Institute of Virology"
    assert body["expertise"].startswith("Viral genome assembly")
    roles = {item["public_name"]: item["role"] for item in body["analyses"]}
    assert roles == {
        "Respiratory virus RT-PCR detection": "contributor",
        "Viral whole genome sequencing": "lead",
    }


def test_analysis_detail_carries_all_three_relationships(seeded: TestClient) -> None:
    analyses = _get(seeded, "/catalog/institution-analyses")
    analysis_id = next(
        item["id"]
        for item in analyses
        if item["public_name"] == "Respiratory virus RT-PCR detection"
    )

    body = _get(seeded, f"/catalog/institution-analyses/{analysis_id}")

    assert body["analysis_type"]["name"] == "Real-Time PCR Detection"
    assert body["institution"]["name"] == "Institute of Virology"
    assert [item["display_name"] for item in body["instruments"]] == ["QuantStudio 7"]
    assert body["instruments"][0]["usage"] == "required"
    assert len(body["targets"]) == 3
    assert {person["full_name"] for person in body["researchers"]} == {
        "Milica Petrovic",
        "Nikola Ilic",
    }


def test_instrument_detail_names_the_analyses_that_use_it(seeded: TestClient) -> None:
    instruments = _get(seeded, "/catalog/institution-instruments")
    instrument_id = next(
        item["id"] for item in instruments if item["display_name"] == "QuantStudio 7"
    )

    body = _get(seeded, f"/catalog/institution-instruments/{instrument_id}")

    assert body["instrument_type"]["name"] == "Real-Time PCR System"
    assert body["manufacturer"] == "Thermo Fisher Scientific"
    assert [item["public_name"] for item in body["analyses"]] == [
        "Respiratory virus RT-PCR detection"
    ]


def test_an_unlinked_instrument_reports_no_analyses(seeded: TestClient) -> None:
    """The seed leaves the shared chemistry PCR unit deliberately unlinked."""
    instruments = _get(seeded, "/catalog/institution-instruments")
    instrument_id = next(
        item["id"] for item in instruments if item["display_name"] == "Shared PCR unit"
    )

    body = _get(seeded, f"/catalog/institution-instruments/{instrument_id}")

    assert body["analyses"] == []


def test_microorganism_detail_names_every_offering_that_targets_it(
    seeded: TestClient,
) -> None:
    organism_id = _id_of(
        seeded, "/catalog/microorganisms", "scientific_name", "Escherichia coli"
    )

    body = _get(seeded, f"/catalog/microorganisms/{organism_id}")

    institutions = sorted(item["institution"]["name"] for item in body["analyses"])
    assert institutions == [
        "Environmental Research Center",
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
    ]


def test_instrument_type_detail_groups_the_owning_institutions(seeded: TestClient) -> None:
    type_id = _id_of(seeded, "/catalog/instrument-types", "name", "Real-Time PCR System")

    body = _get(seeded, f"/catalog/instrument-types/{type_id}")

    assert len(body["instruments"]) == 4
    assert [item["name"] for item in body["institutions"]] == [
        "Center for Analytical Chemistry",
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
        "Institute of Virology",
    ]


def test_analysis_type_detail_lists_every_institution_offering_it(seeded: TestClient) -> None:
    type_id = _id_of(seeded, "/catalog/analysis-types", "name", "Whole Genome Sequencing")

    body = _get(seeded, f"/catalog/analysis-types/{type_id}")

    assert [item["institution"]["name"] for item in body["analyses"]] == [
        "Institute of Virology",
        "Institute of Molecular Genetics",
    ]


@pytest.mark.parametrize(
    "path",
    [
        "/catalog/institutions/999",
        "/catalog/researchers/999",
        "/catalog/institution-instruments/999",
        "/catalog/institution-analyses/999",
        "/catalog/microorganisms/999",
        "/catalog/instrument-types/999",
        "/catalog/analysis-types/999",
    ],
)
def test_a_missing_record_answers_404(client: TestClient, path: str) -> None:
    assert client.get(f"/api/v1{path}").status_code == 404


def test_seeded_institutions_carry_map_coordinates(seeded: TestClient) -> None:
    institution_id = _id_of(
        seeded, "/catalog/institutions", "name", "Environmental Research Center"
    )

    body = _get(seeded, f"/catalog/institutions/{institution_id}")

    assert body["latitude"] == 43.3247
    assert body["longitude"] == 21.9033
