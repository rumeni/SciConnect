from fastapi.testclient import TestClient


def _create(client: TestClient, path: str, payload: dict) -> dict:
    response = client.post(f"/api/v1{path}", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _build_institution(client: TestClient, name: str = "New Institute") -> dict:
    return _create(
        client,
        "/catalog/institutions",
        {"name": name, "city": "Belgrade", "country": "Serbia"},
    )


def test_a_full_capability_can_be_created_and_then_found(client: TestClient) -> None:
    institution = _build_institution(client)
    instrument_type = _create(client, "/catalog/instrument-types", {"name": "PCR System"})
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    organism = _create(client, "/catalog/microorganisms", {"scientific_name": "SARS-CoV-2"})
    researcher = _create(
        client,
        "/catalog/researchers",
        {
            "institution_id": institution["id"],
            "full_name": "Milica Petrovic",
            "title": "Principal Investigator",
        },
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
            "turnaround_days": 2,
        },
    )

    analysis_path = f"/institution-analyses/{analysis['id']}"
    _create(
        client, f"{analysis_path}/instruments", {"institution_instrument_id": instrument["id"]}
    )
    _create(client, f"{analysis_path}/targets", {"microorganism_id": organism["id"]})
    _create(
        client,
        f"{analysis_path}/researchers",
        {"researcher_id": researcher["id"], "role": "lead"},
    )

    search = client.get(
        "/api/v1/capabilities/search",
        params={
            "analysis_type_ids": analysis_type["id"],
            "instrument_type_ids": instrument_type["id"],
            "microorganism_ids": organism["id"],
            "researcher_ids": researcher["id"],
        },
    )
    assert search.status_code == 200
    body = search.json()
    assert body["total"] == 1

    matched = body["items"][0]["matched_analyses"][0]
    assert matched["public_name"] == "Respiratory virus RT-PCR"
    assert [item["display_name"] for item in matched["instruments"]] == ["QuantStudio 7"]
    assert [item["scientific_name"] for item in matched["targets"]] == ["SARS-CoV-2"]
    assert [item["full_name"] for item in matched["researchers"]] == ["Milica Petrovic"]
    assert matched["researchers"][0]["role"] == "lead"


def test_institution_slug_is_derived_from_the_name(client: TestClient) -> None:
    institution = _build_institution(client, "Institute of Virology")
    assert institution["slug"] == "institute-of-virology"


def test_a_duplicate_institution_slug_is_rejected(client: TestClient) -> None:
    _build_institution(client, "Institute of Virology")
    response = client.post(
        "/api/v1/catalog/institutions",
        json={"name": "Institute of Virology", "city": "Nis", "country": "Serbia"},
    )
    assert response.status_code == 409


def test_a_researcher_cannot_be_linked_across_institutions(client: TestClient) -> None:
    owner = _build_institution(client, "Owner Institute")
    outsider = _build_institution(client, "Outsider Institute")
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {"institution_id": owner["id"], "analysis_type_id": analysis_type["id"]},
    )
    outside_researcher = _create(
        client,
        "/catalog/researchers",
        {"institution_id": outsider["id"], "full_name": "Outside Researcher"},
    )

    response = client.post(
        f"/api/v1/institution-analyses/{analysis['id']}/researchers",
        json={"researcher_id": outside_researcher["id"]},
    )
    assert response.status_code == 400
    assert "same institution" in response.json()["detail"]


def test_an_instrument_cannot_be_linked_across_institutions(client: TestClient) -> None:
    owner = _build_institution(client, "Owner Institute")
    outsider = _build_institution(client, "Outsider Institute")
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    instrument_type = _create(client, "/catalog/instrument-types", {"name": "PCR System"})
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {"institution_id": owner["id"], "analysis_type_id": analysis_type["id"]},
    )
    outside_instrument = _create(
        client,
        "/catalog/institution-instruments",
        {"institution_id": outsider["id"], "instrument_type_id": instrument_type["id"]},
    )

    response = client.post(
        f"/api/v1/institution-analyses/{analysis['id']}/instruments",
        json={"institution_instrument_id": outside_instrument["id"]},
    )
    assert response.status_code == 400


def test_the_same_link_cannot_be_created_twice(client: TestClient) -> None:
    institution = _build_institution(client)
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    organism = _create(client, "/catalog/microorganisms", {"scientific_name": "SARS-CoV-2"})
    analysis = _create(
        client,
        "/catalog/institution-analyses",
        {"institution_id": institution["id"], "analysis_type_id": analysis_type["id"]},
    )
    path = f"/api/v1/institution-analyses/{analysis['id']}/targets"

    assert client.post(path, json={"microorganism_id": organism["id"]}).status_code == 201
    assert client.post(path, json={"microorganism_id": organism["id"]}).status_code == 409


def test_an_institution_cannot_offer_the_same_analysis_type_twice(client: TestClient) -> None:
    institution = _build_institution(client)
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})
    payload = {"institution_id": institution["id"], "analysis_type_id": analysis_type["id"]}

    _create(client, "/catalog/institution-analyses", payload)
    response = client.post("/api/v1/catalog/institution-analyses", json=payload)
    assert response.status_code == 409


def test_writes_referencing_a_missing_record_return_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/catalog/researchers", json={"institution_id": 999, "full_name": "Ghost"}
    )
    assert response.status_code == 404


def test_a_non_positive_turnaround_is_rejected_before_reaching_the_database(
    client: TestClient,
) -> None:
    institution = _build_institution(client)
    analysis_type = _create(client, "/catalog/analysis-types", {"name": "PCR analysis"})

    response = client.post(
        "/api/v1/catalog/institution-analyses",
        json={
            "institution_id": institution["id"],
            "analysis_type_id": analysis_type["id"],
            "turnaround_days": 0,
        },
    )
    assert response.status_code == 422


def test_researchers_can_be_listed_per_institution(client: TestClient) -> None:
    first = _build_institution(client, "First Institute")
    second = _build_institution(client, "Second Institute")
    _create(
        client,
        "/catalog/researchers",
        {"institution_id": first["id"], "full_name": "First Person"},
    )
    _create(
        client,
        "/catalog/researchers",
        {"institution_id": second["id"], "full_name": "Second Person"},
    )

    response = client.get("/api/v1/catalog/researchers", params={"institution_id": first["id"]})
    assert response.status_code == 200
    assert [item["full_name"] for item in response.json()] == ["First Person"]


def test_an_institution_can_be_created_with_map_coordinates(client: TestClient) -> None:
    created = _create(
        client,
        "/catalog/institutions",
        {
            "name": "Mapped Institute",
            "city": "Belgrade",
            "country": "Serbia",
            "latitude": 44.8069,
            "longitude": 20.4744,
        },
    )

    assert created["latitude"] == 44.8069
    body = client.get(f"/api/v1/catalog/institutions/{created['id']}").json()
    assert (body["latitude"], body["longitude"]) == (44.8069, 20.4744)


def test_an_institution_without_coordinates_reports_them_as_null(client: TestClient) -> None:
    created = _build_institution(client)

    body = client.get(f"/api/v1/catalog/institutions/{created['id']}").json()

    assert body["latitude"] is None
    assert body["longitude"] is None


def test_one_coordinate_without_the_other_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/catalog/institutions",
        json={
            "name": "Half Mapped",
            "city": "Belgrade",
            "country": "Serbia",
            "latitude": 44.8069,
        },
    )

    assert response.status_code == 422
    assert "together" in response.text


def test_a_coordinate_outside_its_range_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/catalog/institutions",
        json={
            "name": "Off The Globe",
            "city": "Belgrade",
            "country": "Serbia",
            "latitude": 120.0,
            "longitude": 20.0,
        },
    )

    assert response.status_code == 422
