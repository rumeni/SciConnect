import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.seed import seed_catalog


@pytest.fixture
def seeded(client: TestClient, db: Session) -> TestClient:
    seed_catalog(db)
    db.commit()
    return client


def _id_of(client: TestClient, path: str, field: str, value: str) -> int:
    for item in client.get(f"/api/v1{path}").json():
        if item[field] == value:
            return item["id"]
    raise AssertionError(f"{value} not found in {path}")


def _analysis(client: TestClient, public_name: str) -> dict:
    listed = client.get("/api/v1/catalog/institution-analyses").json()
    found = next(item for item in listed if item["public_name"] == public_name)
    return client.get(f"/api/v1/catalog/institution-analyses/{found['id']}").json()


# --- Disconnecting ----------------------------------------------------------


def test_a_researcher_can_stop_performing_an_analysis(seeded: TestClient) -> None:
    analysis = _analysis(seeded, "Respiratory virus RT-PCR detection")
    researcher = next(
        person for person in analysis["researchers"] if person["full_name"] == "Nikola Ilic"
    )

    response = seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/researchers/{researcher['id']}"
    )

    assert response.status_code == 200
    after = seeded.get(f"/api/v1/catalog/institution-analyses/{analysis['id']}").json()
    assert [p["full_name"] for p in after["researchers"]] == ["Milica Petrovic"]


def test_disconnecting_leaves_both_records_standing(seeded: TestClient) -> None:
    analysis = _analysis(seeded, "Respiratory virus RT-PCR detection")
    researcher_id = analysis["researchers"][0]["id"]

    seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/researchers/{researcher_id}"
    )

    assert seeded.get(f"/api/v1/catalog/researchers/{researcher_id}").status_code == 200
    assert (
        seeded.get(f"/api/v1/catalog/institution-analyses/{analysis['id']}").status_code
        == 200
    )


def test_an_analysis_can_stop_using_an_instrument(seeded: TestClient) -> None:
    analysis = _analysis(seeded, "Respiratory virus RT-PCR detection")
    instrument_id = analysis["instruments"][0]["id"]

    response = seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/instruments/{instrument_id}"
    )

    assert response.status_code == 200
    after = seeded.get(f"/api/v1/catalog/institution-analyses/{analysis['id']}").json()
    assert after["instruments"] == []
    assert seeded.get(f"/api/v1/catalog/institution-instruments/{instrument_id}").status_code == 200


def test_an_analysis_can_stop_targeting_an_organism(seeded: TestClient) -> None:
    analysis = _analysis(seeded, "Respiratory virus RT-PCR detection")
    organism_id = next(
        t["id"] for t in analysis["targets"] if t["scientific_name"] == "SARS-CoV-2"
    )

    response = seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/targets/{organism_id}"
    )

    assert response.status_code == 200
    after = seeded.get(f"/api/v1/catalog/institution-analyses/{analysis['id']}").json()
    assert "SARS-CoV-2" not in [t["scientific_name"] for t in after["targets"]]


def test_disconnecting_removes_it_from_search(seeded: TestClient) -> None:
    """The point of the link: without it, the combination stops matching."""
    analysis = _analysis(seeded, "Viral whole genome sequencing")
    researcher_id = analysis["researchers"][0]["id"]
    before = seeded.get(
        "/api/v1/capabilities/search", params={"researcher_ids": researcher_id}
    ).json()
    assert any(
        a["public_name"] == "Viral whole genome sequencing"
        for item in before["items"]
        for a in item["matched_analyses"]
    )

    seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/researchers/{researcher_id}"
    )

    after = seeded.get(
        "/api/v1/capabilities/search", params={"researcher_ids": researcher_id}
    ).json()
    assert not any(
        a["public_name"] == "Viral whole genome sequencing"
        for item in after["items"]
        for a in item["matched_analyses"]
    )


def test_disconnecting_something_never_connected_answers_404(seeded: TestClient) -> None:
    analysis = _analysis(seeded, "Quantitative proteomics service")

    response = seeded.delete(
        f"/api/v1/institution-analyses/{analysis['id']}/researchers/9999"
    )

    assert response.status_code == 404


# --- Deleting ---------------------------------------------------------------


def test_a_researcher_who_has_left_can_be_deleted(seeded: TestClient) -> None:
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Nikola Ilic")

    response = seeded.delete(f"/api/v1/catalog/researchers/{researcher_id}")

    assert response.status_code == 200
    assert response.json()["label"] == "Nikola Ilic"
    assert seeded.get(f"/api/v1/catalog/researchers/{researcher_id}").status_code == 404


def test_deleting_a_researcher_takes_their_analysis_links(seeded: TestClient) -> None:
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Nikola Ilic")

    body = seeded.delete(f"/api/v1/catalog/researchers/{researcher_id}").json()

    assert body["also_removed"] == {"analysis links": 2}
    analysis = _analysis(seeded, "Viral whole genome sequencing")
    assert analysis["researchers"] == []


def test_deleting_a_researcher_leaves_their_institution_alone(seeded: TestClient) -> None:
    institution_id = _id_of(seeded, "/catalog/institutions", "name", "Institute of Virology")
    researcher_id = _id_of(seeded, "/catalog/researchers", "full_name", "Nikola Ilic")

    seeded.delete(f"/api/v1/catalog/researchers/{researcher_id}")

    institution = seeded.get(f"/api/v1/catalog/institutions/{institution_id}").json()
    assert [p["full_name"] for p in institution["researchers"]] == ["Milica Petrovic"]


def test_a_catalog_type_still_in_use_is_refused(seeded: TestClient) -> None:
    type_id = _id_of(seeded, "/catalog/instrument-types", "name", "Real-Time PCR System")

    response = seeded.delete(f"/api/v1/catalog/instrument-types/{type_id}")

    assert response.status_code == 409
    assert "4 instrument(s)" in response.json()["detail"]
    assert seeded.get(f"/api/v1/catalog/instrument-types/{type_id}").status_code == 200


def test_an_organism_still_targeted_is_refused(seeded: TestClient) -> None:
    organism_id = _id_of(
        seeded, "/catalog/microorganisms", "scientific_name", "SARS-CoV-2"
    )

    response = seeded.delete(f"/api/v1/catalog/microorganisms/{organism_id}")

    assert response.status_code == 409
    assert "Disconnect those first" in response.json()["detail"]


def test_an_unused_catalog_entry_can_be_deleted(client: TestClient) -> None:
    created = client.post(
        "/api/v1/catalog/instrument-types", json={"name": "Unused Type"}
    ).json()

    response = client.delete(f"/api/v1/catalog/instrument-types/{created['id']}")

    assert response.status_code == 200
    assert client.get("/api/v1/catalog/instrument-types").json() == []


def test_an_institution_holding_records_is_refused_by_default(seeded: TestClient) -> None:
    institution_id = _id_of(seeded, "/catalog/institutions", "name", "Institute of Virology")

    response = seeded.delete(f"/api/v1/catalog/institutions/{institution_id}")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "2 instruments" in detail and "2 researchers" in detail
    assert seeded.get(f"/api/v1/catalog/institutions/{institution_id}").status_code == 200


def test_an_institution_can_be_deleted_with_its_contents_when_asked(
    seeded: TestClient,
) -> None:
    institution_id = _id_of(seeded, "/catalog/institutions", "name", "Institute of Virology")

    response = seeded.delete(
        f"/api/v1/catalog/institutions/{institution_id}", params={"cascade": "true"}
    )

    assert response.status_code == 200
    assert response.json()["also_removed"] == {
        "instruments": 2,
        "analyses": 2,
        "researchers": 2,
    }
    assert seeded.get(f"/api/v1/catalog/institutions/{institution_id}").status_code == 404
    remaining = [i["full_name"] for i in seeded.get("/api/v1/catalog/researchers").json()]
    assert "Nikola Ilic" not in remaining


def test_an_empty_institution_needs_no_cascade(client: TestClient) -> None:
    created = client.post(
        "/api/v1/catalog/institutions",
        json={"name": "Empty Institute", "city": "Nis", "country": "Serbia"},
    ).json()

    response = client.delete(f"/api/v1/catalog/institutions/{created['id']}")

    assert response.status_code == 200
    assert response.json()["also_removed"] == {}


def test_deleting_an_analysis_offering_keeps_what_it_referenced(
    seeded: TestClient,
) -> None:
    analysis = _analysis(seeded, "Respiratory virus RT-PCR detection")
    instrument_id = analysis["instruments"][0]["id"]

    body = seeded.delete(
        f"/api/v1/catalog/institution-analyses/{analysis['id']}"
    ).json()

    assert body["also_removed"]["target links"] == 3
    assert seeded.get(f"/api/v1/catalog/institution-instruments/{instrument_id}").status_code == 200


def test_deleting_something_absent_answers_404(seeded: TestClient) -> None:
    assert seeded.delete("/api/v1/catalog/researchers/9999").status_code == 404
    assert seeded.delete("/api/v1/catalog/institutions/9999").status_code == 404
