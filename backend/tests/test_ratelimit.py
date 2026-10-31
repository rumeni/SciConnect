"""The per-client budgets, and the address they are counted against."""

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.core.ratelimit import (
    Limit,
    SlidingWindowCounter,
    client_address,
    parse_limit,
)


class TestParsing:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("20/minute", Limit(20, 60)),
            ("5/second", Limit(5, 1)),
            ("1000/hour", Limit(1000, 3600)),
            ("10/day", Limit(10, 86400)),
            # The short and plural spellings people actually write.
            ("30/min", Limit(30, 60)),
            ("30/m", Limit(30, 60)),
            ("30/minutes", Limit(30, 60)),
            ("  7 / HOUR ", Limit(7, 3600)),
        ],
    )
    def test_a_limit_is_read_as_written(self, text: str, expected: Limit) -> None:
        assert parse_limit(text) == expected

    def test_an_omitted_period_means_per_minute(self) -> None:
        assert parse_limit("15") == Limit(15, 60)

    @pytest.mark.parametrize(
        "text", ["20/fortnight", "many/minute", "0/minute", "-5/minute", "/minute"]
    )
    def test_an_unusable_limit_is_refused_rather_than_guessed(self, text: str) -> None:
        with pytest.raises(ValueError):
            parse_limit(text)


class TestTheWindow:
    """Counting is time-based, so the clock is passed in rather than slept on."""

    def test_requests_are_allowed_up_to_the_limit(self) -> None:
        counter = SlidingWindowCounter()
        limit = Limit(3, 60)

        assert [counter.check("a", limit, now=1.0) for _ in range(3)] == [None] * 3
        assert counter.check("a", limit, now=1.0) is not None

    def test_the_wait_it_reports_is_when_the_oldest_hit_ages_out(self) -> None:
        counter = SlidingWindowCounter()
        limit = Limit(2, 60)
        counter.check("a", limit, now=0.0)
        counter.check("a", limit, now=10.0)

        # At t=30 the oldest hit (t=0) leaves the window at t=60.
        assert counter.check("a", limit, now=30.0) == pytest.approx(30.0)

    def test_a_budget_recovers_as_the_window_slides(self) -> None:
        counter = SlidingWindowCounter()
        limit = Limit(2, 60)
        counter.check("a", limit, now=0.0)
        counter.check("a", limit, now=0.0)

        assert counter.check("a", limit, now=59.0) is not None
        assert counter.check("a", limit, now=61.0) is None

    def test_a_burst_either_side_of_a_boundary_is_still_counted(self) -> None:
        """What a fixed per-minute counter gets wrong: 2 at 0:59 and 2 at 1:01
        is four requests in three seconds, not two windows of two."""
        counter = SlidingWindowCounter()
        limit = Limit(2, 60)

        assert counter.check("a", limit, now=59.0) is None
        assert counter.check("a", limit, now=59.5) is None
        assert counter.check("a", limit, now=61.0) is not None

    def test_clients_do_not_share_a_budget(self) -> None:
        counter = SlidingWindowCounter()
        limit = Limit(1, 60)

        assert counter.check("a", limit, now=1.0) is None
        assert counter.check("b", limit, now=1.0) is None
        assert counter.check("a", limit, now=1.0) is not None

    def test_the_table_does_not_grow_without_bound(self) -> None:
        """A flood of distinct addresses must not become a memory leak."""
        counter = SlidingWindowCounter(max_keys=50)
        limit = Limit(5, 60)

        for index in range(500):
            counter.check(f"client-{index}", limit, now=1.0)

        assert len(counter) <= 50

    def test_entries_that_have_aged_out_are_the_first_to_go(self) -> None:
        counter = SlidingWindowCounter(max_keys=2)
        limit = Limit(5, 60)
        counter.check("old", limit, now=0.0)
        counter.check("recent", limit, now=100_000.0)

        counter.check("new", limit, now=100_000.0)

        assert "old" not in counter._hits
        assert "recent" in counter._hits


class TestTheClientAddress:
    """`X-Forwarded-For` is caller-supplied, so how deep we read it matters."""

    @staticmethod
    def _request(forwarded: str | None, peer: str = "10.0.0.1") -> Request:
        headers = []
        if forwarded is not None:
            headers.append((b"x-forwarded-for", forwarded.encode()))
        return Request(
            {
                "type": "http",
                "method": "GET",
                "path": "/",
                "headers": headers,
                "client": (peer, 1234),
            }
        )

    def test_with_no_proxy_the_socket_address_wins(self) -> None:
        """Otherwise any caller could pick its own identity, and its own budget."""
        request = self._request("1.2.3.4")

        assert client_address(request, trusted_hops=0) == "10.0.0.1"

    def test_with_one_proxy_the_last_entry_is_used(self) -> None:
        """The proxy appends what it saw, so the rightmost entry is the only one
        that was not written by the caller."""
        request = self._request("1.2.3.4")

        assert client_address(request, trusted_hops=1) == "1.2.3.4"

    def test_a_forged_chain_cannot_shift_the_identity(self) -> None:
        """The caller prepends fake hops; with one real proxy the real address
        is still the last one."""
        request = self._request("fake-1, fake-2, 203.0.113.9")

        assert client_address(request, trusted_hops=1) == "203.0.113.9"

    def test_two_proxies_read_one_entry_further_left(self) -> None:
        request = self._request("203.0.113.9, 172.16.0.5")

        assert client_address(request, trusted_hops=2) == "203.0.113.9"

    def test_a_chain_shorter_than_the_hop_count_falls_back_to_its_start(self) -> None:
        request = self._request("203.0.113.9")

        assert client_address(request, trusted_hops=3) == "203.0.113.9"

    def test_a_missing_header_falls_back_to_the_socket(self) -> None:
        request = self._request(None)

        assert client_address(request, trusted_hops=1) == "10.0.0.1"


class TestThroughTheApp:
    def test_reads_are_refused_once_the_budget_is_spent(
        self, client: TestClient, limited
    ) -> None:
        limited(rate_limit_read="3/minute")

        for _ in range(3):
            assert client.get("/api/v1/catalog/institutions").status_code == 200

        response = client.get("/api/v1/catalog/institutions")

        assert response.status_code == 429
        assert int(response.headers["Retry-After"]) >= 1
        assert response.json()["detail"].startswith("Too many requests")

    def test_writes_have_their_own_tighter_budget(
        self, client: TestClient, limited
    ) -> None:
        """Spending the write budget must not stop the catalog being read."""
        limited(rate_limit_write="1/minute", rate_limit_read="100/minute")

        assert (
            client.post(
                "/api/v1/catalog/instrument-types", json={"name": "First"}
            ).status_code
            == 201
        )
        assert (
            client.post(
                "/api/v1/catalog/instrument-types", json={"name": "Second"}
            ).status_code
            == 429
        )
        assert client.get("/api/v1/catalog/instrument-types").status_code == 200

    def test_geocoding_is_limited_apart_from_other_reads(
        self, client: TestClient, limited
    ) -> None:
        """Each call spends an allowance on somebody else's service."""
        limited(rate_limit_geocode="1/minute", rate_limit_read="100/minute")

        # The stub geocoder in the fixture finds nothing, so 404 is a served
        # request; what matters is that the second one never reaches it.
        assert client.get("/api/v1/geocode?q=Novi+Sad").status_code == 404
        assert client.get("/api/v1/geocode?q=Belgrade").status_code == 429
        assert client.get("/api/v1/catalog/institutions").status_code == 200

    def test_health_checks_are_never_limited(self, client: TestClient, limited) -> None:
        """An uptime monitor polling on a schedule must not be mistaken for a
        flood, or an outage would be hidden behind a 429."""
        limited(rate_limit_read="1/minute")

        for _ in range(10):
            assert client.get("/api/v1/health").status_code == 200

    def test_a_served_reply_names_the_budget(self, client: TestClient, limited) -> None:
        limited(rate_limit_read="42/minute")

        headers = client.get("/api/v1/catalog/institutions").headers

        assert headers["RateLimit-Limit"] == "42"
        assert headers["RateLimit-Policy"] == "42;w=60"

    def test_a_refusal_still_carries_the_security_headers(
        self, client: TestClient, limited
    ) -> None:
        limited(rate_limit_read="1/minute")
        client.get("/api/v1/catalog/institutions")

        headers = client.get("/api/v1/catalog/institutions").headers

        assert headers["X-Content-Type-Options"] == "nosniff"

    def test_limiting_off_means_no_counting(self, client: TestClient) -> None:
        """The suite runs in this state, which is what makes it fast."""
        for _ in range(200):
            assert client.get("/api/v1/catalog/institutions").status_code == 200
