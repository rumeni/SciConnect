import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.modules.catalog.geocoding import Location
from app.seed import seed_catalog

BELGRADE = Location(latitude=44.8125, longitude=20.4612, label="Belgrade, Serbia")


@pytest.fixture
def seeded(client: TestClient, db: Session) -> TestClient:
    seed_catalog(db)
    db.commit()
    return client


def test_the_map_lists_every_placed_institution(seeded: TestClient) -> None:
    response = seeded.get("/api/v1/map/institutions")

    assert response.status_code == 200
    points = response.json()
    assert len(points) == 5
    assert all(point["latitude"] and point["longitude"] for point in points)
    first = next(p for p in points if p["name"] == "Institute of Virology")
    assert (first["latitude"], first["longitude"]) == (44.8069, 20.4744)
    assert first["address"] == "Bulevar despota Stefana 142"


def test_an_institution_without_a_position_is_left_off_the_map(
    seeded: TestClient, use_geocoder
) -> None:
    use_geocoder(None)
    seeded.post(
        "/api/v1/catalog/institutions",
        json={"name": "Unplaced Institute", "city": "Nowhere", "country": "Atlantis"},
    )

    names = [point["name"] for point in seeded.get("/api/v1/map/institutions").json()]

    assert "Unplaced Institute" not in names
    assert len(names) == 5


def test_a_draft_institution_is_left_off_the_map(seeded: TestClient, use_geocoder) -> None:
    use_geocoder(BELGRADE)
    seeded.post(
        "/api/v1/catalog/institutions",
        json={
            "name": "Draft Institute",
            "city": "Belgrade",
            "country": "Serbia",
            "status": "draft",
        },
    )

    names = [point["name"] for point in seeded.get("/api/v1/map/institutions").json()]

    assert "Draft Institute" not in names


def test_an_address_can_be_placed_for_a_visitor(client: TestClient, use_geocoder) -> None:
    asked = use_geocoder(BELGRADE)

    response = client.get("/api/v1/geocode", params={"q": "Knez Mihailova 1, Belgrade"})

    assert response.status_code == 200
    assert response.json() == {
        "latitude": 44.8125,
        "longitude": 20.4612,
        "label": "Belgrade, Serbia",
    }
    assert asked == ["Knez Mihailova 1, Belgrade"]


def test_an_address_that_cannot_be_placed_answers_404(
    client: TestClient, use_geocoder
) -> None:
    use_geocoder(None)

    response = client.get("/api/v1/geocode", params={"q": "Qqzzxx Nowhere 99999"})

    assert response.status_code == 404


def test_a_too_short_query_is_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/geocode", params={"q": "a"}).status_code == 422
