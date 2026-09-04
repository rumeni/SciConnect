import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed_catalog


@pytest.fixture
def seeded(client: TestClient, db: Session) -> TestClient:
    seed_catalog(db)
    db.commit()
    return client


def _options(client: TestClient, **params: object) -> dict[str, list[str]]:
    response = client.get("/api/v1/capabilities/filter-options", params=params)
    assert response.status_code == 200, response.text
    return {
        category: [option["label"] for option in options]
        for category, options in response.json().items()
    }


def _id_of(client: TestClient, path: str, field: str, value: str) -> int:
    for item in client.get(f"/api/v1{path}").json():
        if item[field] == value:
            return item["id"]
    raise AssertionError(f"{value} not found in {path}")


def test_with_no_selection_every_reachable_value_is_offered(seeded: TestClient) -> None:
    options = _options(seeded)

    assert len(options["institutions"]) == 5
    assert len(options["researchers"]) == 7
    assert len(options["analysis_types"]) == 6
    # The seed leaves one organism untargeted by any offering.
    assert "Escherichia coli" in options["microorganisms"]


def test_selecting_a_researcher_narrows_the_other_filters(seeded: TestClient) -> None:
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Ivana Nikolic")

    options = _options(seeded, researcher_ids=researcher_id)

    assert options["institutions"] == ["Environmental Research Center"]
    assert options["microorganisms"] == ["Escherichia coli", "Listeria monocytogenes"]
    assert options["analysis_types"] == ["Electron Microscopy", "HPLC Compound Analysis"]
    assert options["instrument_types"] == [
        "Electron Microscope",
        "High-Performance Liquid Chromatograph",
    ]


def test_a_researchers_own_filter_still_offers_every_choice(seeded: TestClient) -> None:
    """Narrowing must not trap the user in their current selection."""
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Ivana Nikolic")

    options = _options(seeded, researcher_ids=researcher_id)

    assert len(options["researchers"]) == 7


def test_selecting_an_institution_narrows_the_researchers(seeded: TestClient) -> None:
    institution_id = _id_of(seeded, "/catalog/institutions", "name", "Institute of Virology")

    options = _options(seeded, institution_ids=institution_id)

    assert options["researchers"] == ["Milica Petrovic", "Nikola Ilic"]
    assert options["microorganisms"] == [
        "Human cytomegalovirus",
        "Influenza A virus",
        "SARS-CoV-2",
    ]


def test_a_researcher_with_no_target_organisms_offers_none(seeded: TestClient) -> None:
    """The chemistry offerings deliberately target no organism."""
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Jelena Markovic")

    options = _options(seeded, researcher_ids=researcher_id)

    assert options["institutions"] == ["Center for Analytical Chemistry"]
    assert options["microorganisms"] == []


def test_every_offered_value_returns_at_least_one_result(seeded: TestClient) -> None:
    """The point of narrowing: no offered combination can be a dead end."""
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Marko Stankovic")
    response = seeded.get(
        "/api/v1/capabilities/filter-options", params={"researcher_ids": researcher_id}
    )
    options = response.json()

    for category, query_name in [
        ("institutions", "institution_ids"),
        ("instrument_types", "instrument_type_ids"),
        ("analysis_types", "analysis_type_ids"),
        ("microorganisms", "microorganism_ids"),
    ]:
        for option in options[category]:
            search = seeded.get(
                "/api/v1/capabilities/search",
                params={"researcher_ids": researcher_id, query_name: option["id"]},
            )
            assert search.json()["total"] >= 1, f"{category} {option['label']} is a dead end"


def test_combining_two_selections_narrows_further(seeded: TestClient) -> None:
    organism_id = _id_of(
        seeded, "/catalog/microorganisms", "scientific_name", "Escherichia coli"
    )

    alone = _options(seeded, microorganism_ids=organism_id)
    assert alone["institutions"] == [
        "Environmental Research Center",
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
    ]

    # Nis drops out; the two Belgrade institutions that target it remain.
    with_city = _options(seeded, microorganism_ids=organism_id, city="Belgrade")
    assert with_city["institutions"] == [
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
    ]
