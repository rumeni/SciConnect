import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.catalog.models import Institution, Microorganism
from app.seed import seed_catalog


@pytest.fixture
def seeded(client: TestClient, db: Session) -> TestClient:
    seed_catalog(db)
    db.commit()
    return client


def _search(client: TestClient, term: str, **params: object) -> list[dict]:
    response = client.get("/api/v1/search", params={"q": term, **params})
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _labels(client: TestClient, term: str) -> list[str]:
    return [item["label"] for item in _search(client, term)]


def test_a_fragment_finds_every_kind_that_carries_it(seeded: TestClient) -> None:
    kinds = {item["kind"] for item in _search(seeded, "PCR")}

    assert kinds == {"instrument-type", "analysis-type", "instrument", "analysis"}


def test_the_match_is_anywhere_in_the_name(seeded: TestClient) -> None:
    assert "Institute of Molecular Genetics" in _labels(seeded, "Molecular")
    assert "Institute of Molecular Genetics" in _labels(seeded, "genetics")


def test_the_match_ignores_case(seeded: TestClient) -> None:
    assert _labels(seeded, "VIROLOGY") == _labels(seeded, "virology")


def test_a_name_starting_with_the_term_is_ranked_first(seeded: TestClient) -> None:
    labels = _labels(seeded, "Institute")

    assert labels[0].startswith("Institute")


def test_a_researcher_is_found_by_either_of_their_names(seeded: TestClient) -> None:
    assert "Milica Petrovic" in _labels(seeded, "Milica")
    assert "Milica Petrovic" in _labels(seeded, "Petrovic")


def test_a_match_carries_what_is_needed_to_open_it(seeded: TestClient) -> None:
    match = next(item for item in _search(seeded, "Nikola Ilic"))

    assert match["kind"] == "researcher"
    assert isinstance(match["id"], int)
    body = seeded.get(f"/api/v1/catalog/researchers/{match['id']}").json()
    assert body["full_name"] == "Nikola Ilic"


def test_a_match_is_labelled_with_enough_context_to_tell_it_apart(
    seeded: TestClient,
) -> None:
    match = next(item for item in _search(seeded, "QuantStudio"))

    assert match["kind"] == "instrument"
    assert "Real-Time PCR System" in match["note"]
    assert "Institute of Virology" in match["note"]


def test_an_organism_is_found_by_its_common_name(client: TestClient, db: Session) -> None:
    db.add(Microorganism(scientific_name="Escherichia coli", common_name="E. coli"))
    db.commit()

    matches = _search(client, "E. coli")

    assert [item["label"] for item in matches] == ["Escherichia coli"]
    assert matches[0]["note"] == "E. coli"


def test_nothing_matching_answers_an_empty_list(seeded: TestClient) -> None:
    assert _search(seeded, "qqzzxx") == []


def test_a_wildcard_is_matched_literally_rather_than_as_a_pattern(
    seeded: TestClient,
) -> None:
    """A bare % would otherwise match every record in the catalogue."""
    assert _search(seeded, "%") == []
    assert _search(seeded, "_") == []


def test_a_record_that_is_not_active_is_found_but_says_so(
    client: TestClient, db: Session
) -> None:
    db.add(
        Institution(
            name="Archived Institute",
            slug="archived-institute",
            city="Nis",
            country="Serbia",
            status="archived",
        )
    )
    db.commit()

    match = next(item for item in _search(client, "Archived"))

    assert match["label"] == "Archived Institute"
    assert "archived" in match["note"]


def test_an_active_record_is_not_cluttered_with_its_status(seeded: TestClient) -> None:
    match = next(item for item in _search(seeded, "Institute of Virology"))

    assert match["note"] == "Belgrade, Serbia"


def test_the_answer_respects_the_requested_cap(seeded: TestClient) -> None:
    assert len(_search(seeded, "e", limit=3)) == 3


def test_truncation_is_reported(seeded: TestClient) -> None:
    body = seeded.get("/api/v1/search", params={"q": "e", "limit": 2}).json()

    assert len(body["items"]) == 2
    assert body["truncated"] is True


def test_an_uncut_answer_is_not_reported_as_truncated(seeded: TestClient) -> None:
    body = seeded.get("/api/v1/search", params={"q": "QuantStudio"}).json()

    assert body["truncated"] is False


def test_a_blank_query_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422
