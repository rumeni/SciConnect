"""The shared Nominatim budget, the result cache and backing off (issue #6).

Every test uses a fake clock, a recording sleep and httpx.MockTransport: no
test waits in real time or reaches the network.
"""

import threading

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.modules.catalog.geocoding import (
    MAX_COOLDOWN_SECONDS,
    GeocodingUnavailable,
    Location,
    NominatimGeocoder,
    default_geocoder,
)

FOUND = [{"lat": "44.8125", "lon": "20.4612", "display_name": "Belgrade, Serbia"}]


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class Upstream:
    """A stand-in Nominatim that counts what reaches it."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []
        self._lock = threading.Lock()

    def __call__(self, request: httpx.Request) -> httpx.Response:
        with self._lock:
            self.requests.append(request)
            reply = self.responses[0] if len(self.responses) == 1 else self.responses.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    @property
    def queries(self) -> list[str]:
        return [request.url.params["q"] for request in self.requests]


@pytest.fixture
def budget(monkeypatch):
    monkeypatch.setattr(settings, "geocoding_min_interval_seconds", 1.0)
    monkeypatch.setattr(settings, "geocoding_max_wait_seconds", 3.0)
    monkeypatch.setattr(settings, "geocoding_cache_ttl_seconds", 7 * 24 * 3600)
    monkeypatch.setattr(settings, "geocoding_negative_cache_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "geocoding_cache_max_entries", 100)
    monkeypatch.setattr(settings, "geocoding_cooldown_seconds", 60.0)


def _geocoder(upstream: Upstream, clock: FakeClock, slept: list[float] | None = None):
    record = slept.append if slept is not None else (lambda _seconds: None)
    return NominatimGeocoder(clock=clock, sleep=record, transport=httpx.MockTransport(upstream))


# --- Cache ----------------------------------------------------------------------


@pytest.mark.usefixtures("budget")
def test_equivalent_queries_reach_the_service_once() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    geocoder = _geocoder(upstream, FakeClock())

    first = geocoder("Kneza Milosa 1, Belgrade")
    second = geocoder("  kneza   MILOSA 1,  belgrade ")

    assert first == second == Location(44.8125, 20.4612, "Belgrade, Serbia")
    assert upstream.queries == ["Kneza Milosa 1, Belgrade"]


@pytest.mark.usefixtures("budget")
def test_a_found_place_expires_after_its_ttl() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    geocoder("Belgrade")
    clock.advance(7 * 24 * 3600 - 1)
    geocoder("Belgrade")
    assert len(upstream.requests) == 1

    clock.advance(2)
    geocoder("Belgrade")
    assert len(upstream.requests) == 2


@pytest.mark.usefixtures("budget")
def test_no_match_is_cached_for_a_shorter_time() -> None:
    upstream = Upstream(httpx.Response(200, json=[]))
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    assert geocoder("Nowhere 999") is None
    clock.advance(3599)
    assert geocoder("Nowhere 999") is None
    assert len(upstream.requests) == 1

    clock.advance(2)
    geocoder("Nowhere 999")
    assert len(upstream.requests) == 2


@pytest.mark.usefixtures("budget")
def test_failures_are_never_cached() -> None:
    upstream = Upstream(httpx.Response(500), httpx.Response(200, json=FOUND))
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable):
        geocoder("Belgrade")
    clock.advance(1)
    assert geocoder("Belgrade") is not None
    assert len(upstream.requests) == 2


def test_the_cache_keeps_only_the_most_recent_entries(budget, monkeypatch) -> None:
    monkeypatch.setattr(settings, "geocoding_cache_max_entries", 2)
    upstream = Upstream(httpx.Response(200, json=FOUND))
    geocoder = _geocoder(upstream, FakeClock())

    for query in ["A city", "B city", "A city", "C city"]:
        geocoder(query)
    # "B city" was least recently used when "C city" arrived.
    geocoder("A city")
    geocoder("B city")

    assert upstream.queries == ["A city", "B city", "C city", "B city"]


# --- Global budget -----------------------------------------------------------------


@pytest.mark.usefixtures("budget")
def test_simultaneous_lookups_are_spaced_one_second_apart() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    slept: list[float] = []
    geocoder = _geocoder(upstream, FakeClock(), slept)

    for n in range(4):
        geocoder(f"Place {n}")

    # The clock never moves, so these all arrive at the same instant.
    assert slept == [1.0, 2.0, 3.0]
    assert len(upstream.requests) == 4


@pytest.mark.usefixtures("budget")
def test_a_lookup_that_would_queue_too_long_is_refused_without_a_request() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    geocoder = _geocoder(upstream, FakeClock())
    for n in range(4):
        geocoder(f"Place {n}")

    with pytest.raises(GeocodingUnavailable):
        geocoder("Place 4")

    assert len(upstream.requests) == 4


@pytest.mark.usefixtures("budget")
def test_cached_answers_do_not_spend_the_budget() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    geocoder = _geocoder(upstream, FakeClock())
    for n in range(4):
        geocoder(f"Place {n}")

    # The queue is full, yet a known place still answers at once.
    assert geocoder("Place 0") is not None


@pytest.mark.usefixtures("budget")
def test_the_budget_refills_as_time_passes() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    clock = FakeClock()
    slept: list[float] = []
    geocoder = _geocoder(upstream, clock, slept)

    geocoder("First")
    clock.advance(1.0)
    geocoder("Second")

    assert slept == []


@pytest.mark.usefixtures("budget")
def test_concurrent_threads_share_one_budget() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    slept: list[float] = []
    geocoder = _geocoder(upstream, FakeClock(), slept)
    outcomes: list[str] = []
    start = threading.Barrier(10)

    def visitor(n: int) -> None:
        start.wait()
        try:
            geocoder(f"Visitor {n} street")
            outcomes.append("found")
        except GeocodingUnavailable:
            outcomes.append("busy")

    threads = [threading.Thread(target=visitor, args=(n,)) for n in range(10)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    # Ten callers at once: the first goes now, three queue for 1, 2 and 3 s,
    # the rest are turned away instead of piling up.
    assert sorted(outcomes) == ["busy"] * 6 + ["found"] * 4
    assert sorted(slept) == [1.0, 2.0, 3.0]
    assert len(upstream.requests) == 4


# --- Backing off -------------------------------------------------------------------


@pytest.mark.usefixtures("budget")
def test_a_429_pauses_every_lookup_for_its_retry_after() -> None:
    upstream = Upstream(
        httpx.Response(429, headers={"Retry-After": "120"}), httpx.Response(200, json=FOUND)
    )
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable):
        geocoder("First")
    clock.advance(119)
    with pytest.raises(GeocodingUnavailable):
        geocoder("Second")
    assert len(upstream.requests) == 1

    clock.advance(2)
    assert geocoder("Second") is not None


@pytest.mark.usefixtures("budget")
def test_a_503_without_retry_after_pauses_for_the_default_cooldown() -> None:
    upstream = Upstream(httpx.Response(503), httpx.Response(200, json=FOUND))
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable):
        geocoder("First")
    clock.advance(59)
    with pytest.raises(GeocodingUnavailable):
        geocoder("First")
    clock.advance(2)
    assert geocoder("First") is not None


@pytest.mark.usefixtures("budget")
def test_an_absurd_retry_after_is_capped() -> None:
    upstream = Upstream(
        httpx.Response(429, headers={"Retry-After": "999999"}), httpx.Response(200, json=FOUND)
    )
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable):
        geocoder("First")
    clock.advance(MAX_COOLDOWN_SECONDS + 1)
    assert geocoder("First") is not None


@pytest.mark.usefixtures("budget")
def test_retry_after_zero_means_no_pause() -> None:
    upstream = Upstream(
        httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(200, json=FOUND)
    )
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable) as raised:
        geocoder("First")
    assert raised.value.retry_after == 0
    clock.advance(1)
    assert geocoder("First") is not None


@pytest.mark.usefixtures("budget")
def test_a_pause_that_starts_while_a_request_waits_stops_it() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    clock = FakeClock()
    geocoder: NominatimGeocoder

    def sleep_while_another_request_is_told_to_back_off(seconds: float) -> None:
        geocoder._back_off(httpx.Response(429, headers={"Retry-After": "30"}))

    geocoder = NominatimGeocoder(
        clock=clock,
        sleep=sleep_while_another_request_is_told_to_back_off,
        transport=httpx.MockTransport(upstream),
    )
    geocoder("First")

    with pytest.raises(GeocodingUnavailable) as raised:
        geocoder("Second")  # queued for 1 s, during which the pause began

    assert raised.value.retry_after == 30
    assert upstream.queries == ["First"]


@pytest.mark.usefixtures("budget")
@pytest.mark.parametrize("status", [400, 404])
def test_a_rejected_query_is_not_found_rather_than_busy(status: int) -> None:
    upstream = Upstream(httpx.Response(status))
    geocoder = _geocoder(upstream, FakeClock())

    assert geocoder("???") is None
    assert geocoder("???") is None
    assert len(upstream.requests) == 1


def test_the_search_tells_clients_how_long_the_pause_lasts(client: TestClient, budget) -> None:
    from app.main import app

    upstream = Upstream(httpx.Response(429, headers={"Retry-After": "1800"}))
    geocoder = _geocoder(upstream, FakeClock())
    app.dependency_overrides[default_geocoder] = lambda: geocoder

    first = client.get("/api/v1/geocode", params={"q": "Belgrade"})
    second = client.get("/api/v1/geocode", params={"q": "Nis"})

    assert first.status_code == second.status_code == 503
    assert first.headers["Retry-After"] == second.headers["Retry-After"] == "1800"
    assert len(upstream.requests) == 1


@pytest.mark.usefixtures("budget")
def test_a_timeout_is_unavailable_and_not_cached() -> None:
    upstream = Upstream(httpx.ReadTimeout("slow"), httpx.Response(200, json=FOUND))
    clock = FakeClock()
    geocoder = _geocoder(upstream, clock)

    with pytest.raises(GeocodingUnavailable):
        geocoder("Belgrade")
    clock.advance(1)
    assert geocoder("Belgrade") is not None


@pytest.mark.usefixtures("budget")
def test_requests_identify_the_deployment() -> None:
    upstream = Upstream(httpx.Response(200, json=FOUND))
    _geocoder(upstream, FakeClock())("Belgrade")

    assert upstream.requests[0].headers["User-Agent"] == settings.geocoding_user_agent


def test_the_default_user_agent_names_a_real_site() -> None:
    assert "example.org" not in Settings().geocoding_user_agent


# --- Both entry points share the same controls -----------------------------------


@pytest.fixture
def shared(client: TestClient, budget):
    """Install one real (but network-free) geocoder behind both endpoints."""
    from app.main import app

    upstream = Upstream(httpx.Response(200, json=FOUND))
    geocoder = _geocoder(upstream, FakeClock())
    app.dependency_overrides[default_geocoder] = lambda: geocoder
    return upstream


def _create(client: TestClient, name: str) -> httpx.Response:
    return client.post(
        "/api/v1/catalog/institutions",
        json={"name": name, "address": "Kneza Milosa 1", "city": "Belgrade", "country": "Serbia"},
    )


def test_search_and_writes_share_the_cache(client: TestClient, shared: Upstream) -> None:
    looked_up = client.get("/api/v1/geocode", params={"q": "Kneza Milosa 1, Belgrade, Serbia"})
    assert looked_up.status_code == 200

    created = _create(client, "Cached Institute")

    assert created.status_code == 201, created.text
    assert created.json()["latitude"] == 44.8125
    assert len(shared.requests) == 1


def test_search_and_writes_share_the_budget(client: TestClient, shared: Upstream) -> None:
    for n in range(4):
        assert client.get("/api/v1/geocode", params={"q": f"Place {n}"}).status_code == 200

    busy = client.get("/api/v1/geocode", params={"q": "Place 4"})
    assert busy.status_code == 503
    # The queue is 4 s long and may be 3 s: a slot frees up in 1 s.
    assert busy.headers["Retry-After"] == "1"

    # A write while the budget is spent still succeeds, just without a map.
    created = _create(client, "Busy Institute")
    assert created.status_code == 201, created.text
    assert created.json()["latitude"] is None
    assert len(shared.requests) == 4


def test_production_refuses_a_faster_rate_against_public_nominatim() -> None:
    safe = {
        "app_env": "production",
        "admin_token": "a" * 48,
        "cors_origins": ["https://sciconnect.rs"],
        "allowed_hosts": ["sciconnect.rs"],
        "database_url": "postgresql+psycopg://u:p@db:5432/sciconnect",
    }
    assert Settings(**safe).geocoding_min_interval_seconds == 1.0

    with pytest.raises(ValueError, match="one request per second"):
        Settings(**safe, geocoding_min_interval_seconds=0.5)

    # A self-hosted instance sets its own limits.
    Settings(
        **safe,
        geocoding_min_interval_seconds=0,
        geocoding_url="https://geo.internal.example/search",
    )
