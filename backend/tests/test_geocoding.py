import httpx
import pytest
from fastapi.testclient import TestClient

from app.modules.catalog.geocoding import Location, address_query, nominatim_geocoder

BELGRADE = Location(latitude=44.8125, longitude=20.4612, label="Bulevar oslobodjenja 18")


def _create(client: TestClient, **fields: object) -> dict:
    payload = {"name": "Mapped Institute", "city": "Belgrade", "country": "Serbia"}
    payload.update(fields)
    response = client.post("/api/v1/catalog/institutions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_an_address_is_turned_into_coordinates(client: TestClient, use_geocoder) -> None:
    asked = use_geocoder(BELGRADE)

    created = _create(client, address="Bulevar oslobodjenja 18")

    assert asked == ["Bulevar oslobodjenja 18, Belgrade, Serbia"]
    assert (created["latitude"], created["longitude"]) == (44.8125, 20.4612)
    assert created["address"] == "Bulevar oslobodjenja 18"


def test_the_city_and_country_are_looked_up_when_no_street_is_given(
    client: TestClient, use_geocoder
) -> None:
    asked = use_geocoder(BELGRADE)

    _create(client)

    assert asked == ["Belgrade, Serbia"]


def test_an_address_that_cannot_be_found_still_creates_the_institution(
    client: TestClient, use_geocoder
) -> None:
    use_geocoder(None)

    created = _create(client, address="Nowhere at all 999")

    assert created["address"] == "Nowhere at all 999"
    assert created["latitude"] is None
    assert created["longitude"] is None


def test_explicit_coordinates_win_and_skip_the_lookup(
    client: TestClient, use_geocoder
) -> None:
    asked = use_geocoder(BELGRADE)

    created = _create(client, address="Somewhere", latitude=10.0, longitude=20.0)

    assert asked == []
    assert (created["latitude"], created["longitude"]) == (10.0, 20.0)


def test_the_looked_up_position_reaches_the_detail_view(
    client: TestClient, use_geocoder
) -> None:
    use_geocoder(BELGRADE)
    created = _create(client, address="Bulevar oslobodjenja 18")

    body = client.get(f"/api/v1/catalog/institutions/{created['id']}").json()

    assert body["address"] == "Bulevar oslobodjenja 18"
    assert (body["latitude"], body["longitude"]) == (44.8125, 20.4612)


@pytest.mark.parametrize(
    ("address", "city", "country", "expected"),
    [
        ("Street 1", "Belgrade", "Serbia", "Street 1, Belgrade, Serbia"),
        (None, "Belgrade", "Serbia", "Belgrade, Serbia"),
        ("  ", "Belgrade", "Serbia", "Belgrade, Serbia"),
        (None, None, None, None),
    ],
)
def test_the_lookup_query_uses_the_most_specific_address_available(
    address: str | None, city: str | None, country: str | None, expected: str | None
) -> None:
    assert address_query(address, city, country) == expected


def _geocoder_against(handler) -> Location | None:
    """Run the real geocoder against a stubbed transport, never the network."""
    transport = httpx.MockTransport(handler)
    original = httpx.get

    def patched(url, **kwargs):
        with httpx.Client(transport=transport) as stub_client:
            return stub_client.get(url, **kwargs)

    httpx.get = patched
    try:
        return nominatim_geocoder("Bulevar oslobodjenja 18, Belgrade, Serbia")
    finally:
        httpx.get = original


def test_the_geocoder_reads_a_nominatim_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Bulevar" in request.url.params["q"]
        assert request.url.params["format"] == "jsonv2"
        return httpx.Response(
            200,
            json=[{"lat": "44.8125", "lon": "20.4612", "display_name": "Bulevar, Belgrade"}],
        )

    located = _geocoder_against(handler)

    assert located == Location(44.8125, 20.4612, "Bulevar, Belgrade")


def test_the_geocoder_treats_no_match_as_no_location() -> None:
    assert _geocoder_against(lambda request: httpx.Response(200, json=[])) is None


def test_a_failing_geocoding_service_does_not_raise() -> None:
    assert _geocoder_against(lambda request: httpx.Response(503)) is None


def test_an_unusable_match_does_not_raise() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"lat": "not-a-number", "lon": "20.0"}])

    assert _geocoder_against(handler) is None
