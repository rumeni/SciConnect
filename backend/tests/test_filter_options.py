import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import ANALYSIS_TYPES, INSTITUTIONS, seed_catalog

EXPECTED_RESEARCHERS = sum(len(spec["researchers"]) for spec in INSTITUTIONS)


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

    assert len(options["institutions"]) == len(INSTITUTIONS)
    assert len(options["researchers"]) == EXPECTED_RESEARCHERS
    assert len(options["analysis_types"]) == len(ANALYSIS_TYPES)
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

    assert len(options["researchers"]) == EXPECTED_RESEARCHERS


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


CATEGORIES = [
    ("institutions", "institution_ids"),
    ("instrument_types", "instrument_type_ids"),
    ("analysis_types", "analysis_type_ids"),
    ("microorganisms", "microorganism_ids"),
    ("researchers", "researcher_ids"),
]


def _assert_no_dead_ends(client: TestClient, selection: dict[str, object]) -> int:
    options = client.get("/api/v1/capabilities/filter-options", params=selection).json()
    offered = 0
    for category, query_name in CATEGORIES:
        for option in options[category]:
            offered += 1
            search = client.get(
                "/api/v1/capabilities/search",
                params={**selection, query_name: option["id"]},
            )
            assert search.json()["total"] >= 1, (
                f"{category} '{option['label']}' is a dead end with {selection}"
            )
    return offered


def test_every_offered_value_returns_at_least_one_result(seeded: TestClient) -> None:
    """The point of narrowing: no offered combination can be a dead end."""
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Marko Stankovic")

    assert _assert_no_dead_ends(seeded, {"researcher_ids": researcher_id}) > 0


def test_an_analysis_filter_does_not_offer_unlinked_instruments(
    seeded: TestClient,
) -> None:
    """With an analysis selected, search needs the instrument linked to it.

    Offering everything the institution happens to own proposed combinations
    the search could not satisfy, which this covers from the other direction.
    """
    analysis_id = _id_of(seeded, "/catalog/analysis-types", "name", "Real-Time PCR Detection")

    options = _options(seeded, analysis_type_ids=analysis_id)

    assert options["instrument_types"] == [
        "Automated Nucleic Acid Extractor",
        "Real-Time PCR System",
    ]
    assert "Flow Cytometer" not in options["instrument_types"]
    assert "Next-Generation Sequencer" not in options["instrument_types"]


def test_an_analysis_filter_only_offers_researchers_who_perform_it(
    seeded: TestClient,
) -> None:
    analysis_id = _id_of(seeded, "/catalog/analysis-types", "name", "Real-Time PCR Detection")

    offered = _options(seeded, analysis_type_ids=analysis_id)["researchers"]

    # Employed where the analysis is offered, but assigned to other offerings.
    assert "Petar Lazic" not in offered
    assert "Aleksandar Ristic" not in offered
    assert "Milica Petrovic" in offered


@pytest.mark.parametrize(
    "selection",
    [
        {},
        {"analysis_type_ids": "Real-Time PCR Detection"},
        {"microorganism_ids": "Escherichia coli"},
    ],
    ids=["nothing selected", "analysis selected", "organism selected"],
)
def test_no_selection_leads_to_a_dead_end(
    seeded: TestClient, selection: dict[str, str]
) -> None:
    """Every entry point, not just the one that happened to be safe."""
    resolved: dict[str, object] = {}
    for key, name in selection.items():
        if key == "analysis_type_ids":
            resolved[key] = _id_of(seeded, "/catalog/analysis-types", "name", name)
        else:
            resolved[key] = _id_of(
                seeded, "/catalog/microorganisms", "scientific_name", name
            )

    assert _assert_no_dead_ends(seeded, resolved) > 0


def test_combining_two_selections_narrows_further(seeded: TestClient) -> None:
    organism_id = _id_of(
        seeded, "/catalog/microorganisms", "scientific_name", "Escherichia coli"
    )

    alone = _options(seeded, microorganism_ids=organism_id)
    assert alone["institutions"] == [
        "Clinical Microbiology Laboratory Vojvodina",
        "Environmental Research Center",
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
        "Institute of Soil Microbiology",
        "National Reference Laboratory for Water Microbiology",
    ]

    # Novi Sad, Nis and Subotica drop out; the Belgrade pair remains.
    with_city = _options(seeded, microorganism_ids=organism_id, city="Belgrade")
    assert with_city["institutions"] == [
        "Faculty of Veterinary Medicine Core Facility",
        "Institute of Molecular Genetics",
    ]
