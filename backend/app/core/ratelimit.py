"""Per-client request limits.

The catalog is public and every read hits the database, the geocoding proxy
spends an allowance on a third-party service, and the write endpoints change
data. None of that should be reachable as fast as a script can ask, so each
client address gets a budget per class of request.

The window is a sliding log: the arrival times of a client's recent requests,
trimmed to the window on every check. That costs a little more memory than a
fixed counter and in exchange it cannot be gamed by sending a burst either side
of a window boundary.

Scope: the counters live in this process. Two API workers would therefore allow
twice the configured rate, which is why the deployment runs a single worker per
container and would need a shared store before scaling out.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass

from starlette.datastructures import MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import Settings, settings

PERIOD_SECONDS = {
    "second": 1,
    "sec": 1,
    "s": 1,
    "minute": 60,
    "min": 60,
    "m": 60,
    "hour": 3600,
    "h": 3600,
    "day": 86400,
    "d": 86400,
}

# Liveness and readiness are polled by uptime monitors on a fixed schedule from
# a handful of addresses; counting them would turn ordinary monitoring into a
# refusal and hide a real outage behind a 429.
EXEMPT_PATHS = frozenset({"/api/v1/health", "/api/v1/health/database"})

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
READ_METHODS = frozenset({"GET", "HEAD"})

# Where a browser asks whether its admin key is right. Counted on its own, so
# guessing at the key cannot borrow the more generous write budget.
AUTH_CHECK_PATH = "/api/v1/auth/check"


@dataclass(frozen=True)
class Limit:
    """How many requests are allowed, and over how long."""

    count: int
    seconds: int

    def __str__(self) -> str:
        return f"{self.count}/{self.seconds}s"


def parse_limit(text: str) -> Limit:
    """Read a limit written as "20/minute".

    Raises ValueError, which while loading settings means the process refuses to
    start rather than quietly running with a limit nobody intended.
    """
    raw_count, _, raw_period = text.strip().partition("/")
    period = raw_period.strip().lower() or "minute"
    seconds = PERIOD_SECONDS.get(period) or PERIOD_SECONDS.get(period.rstrip("s"))
    if seconds is None:
        raise ValueError(
            f"Unknown rate limit period {raw_period!r} in {text!r}; "
            f"use one of {sorted(set(PERIOD_SECONDS))}"
        )
    try:
        count = int(raw_count)
    except ValueError as error:
        raise ValueError(f"Rate limit {text!r} does not start with a number") from error
    if count < 1:
        raise ValueError(f"Rate limit {text!r} must allow at least one request")
    return Limit(count=count, seconds=seconds)


class SlidingWindowCounter:
    """Arrival times per key, trimmed to the window on each check.

    Checks run inside the event loop and never await, so the dictionary is only
    ever touched by one task at a time and needs no lock.
    """

    def __init__(self, max_keys: int = 20_000) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._max_keys = max_keys

    def check(self, key: str, limit: Limit, now: float | None = None) -> float | None:
        """Record a request. Returns None when allowed, else seconds to wait."""
        now = time.monotonic() if now is None else now
        cutoff = now - limit.seconds

        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self._max_keys:
                self._evict(now)
            hits = self._hits.setdefault(key, deque())

        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= limit.count:
            # The oldest hit in the window is what has to age out before the
            # next request fits.
            return max(0.0, hits[0] - cutoff)

        hits.append(now)
        return None

    def _evict(self, now: float) -> None:
        """Make room when the table is full.

        Called only on a miss against a full table, so the cost falls on
        whoever is filling it rather than on every request.
        """
        longest = max(PERIOD_SECONDS.values())
        stale = [
            key for key, hits in self._hits.items() if not hits or hits[-1] <= now - longest
        ]
        for key in stale:
            del self._hits[key]
        if not stale:
            # Everything is live: forget the least recently active half rather
            # than letting the table grow without bound.
            by_age = sorted(self._hits, key=lambda key: self._hits[key][-1])
            for key in by_age[: max(1, len(by_age) // 2)]:
                del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()

    def __len__(self) -> int:
        return len(self._hits)


def client_address(request: Request, trusted_hops: int) -> str:
    """The caller's address, read only as deep into `X-Forwarded-For` as trusted.

    Anyone can send `X-Forwarded-For`. Each proxy appends the address it saw, so
    with one trusted proxy in front the last entry is the one that proxy wrote
    and everything to its left is the client's own claim. Counting from the
    right by the number of proxies actually deployed is what makes the value
    trustworthy: without it, a flood could spend a fresh budget per request by
    inventing an address each time.
    """
    if trusted_hops > 0:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            chain = [part.strip() for part in forwarded.split(",") if part.strip()]
            if chain:
                return chain[-min(trusted_hops, len(chain))]
    client = request.client
    return client.host if client else "unknown"


# One table for the process. Keeping it at module level rather than inside the
# middleware instance means a test, or a second mounted app, can clear the
# counts without reaching into the middleware stack to find the instance.
counter = SlidingWindowCounter(max_keys=settings.rate_limit_max_clients)


class RateLimitMiddleware:
    """Applies the read, write and geocoding budgets to every request."""

    def __init__(
        self,
        app: ASGIApp,
        config: Settings | None = None,
        store: SlidingWindowCounter | None = None,
    ) -> None:
        self.app = app
        self._config = config
        self.counter = store or counter

    @property
    def config(self) -> Settings:
        # Read through on every request so a test, or a reload, sees the current
        # settings rather than whatever was in place when the app was built.
        return self._config or settings

    def bucket_for(self, request: Request) -> tuple[str, Limit] | None:
        """Which budget this request draws on, or None when it is exempt."""
        config = self.config
        path = request.url.path.rstrip("/") or "/"

        if path in EXEMPT_PATHS:
            if request.method in READ_METHODS:
                return None
            # Monitors only read. Any other method still meets the admin-key
            # check before routing, so a wrong key answers 401 and a right one
            # 405: that is a key check and spends the key-check budget.
            return "auth", parse_limit(config.rate_limit_auth)
        # A browser preflight is not a second request from the page; refusing it
        # would surface as an opaque CORS failure rather than a 429.
        if request.method == "OPTIONS":
            return None

        if path == AUTH_CHECK_PATH:
            return "auth", parse_limit(config.rate_limit_auth)
        if path == "/api/v1/geocode":
            return "geocode", parse_limit(config.rate_limit_geocode)
        if request.method in UNSAFE_METHODS:
            return "write", parse_limit(config.rate_limit_write)
        return "read", parse_limit(config.rate_limit_read)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self.config.rate_limit_enabled:
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        bucket = self.bucket_for(request)
        if bucket is None:
            await self.app(scope, receive, send)
            return

        name, limit = bucket
        key = f"{name}:{client_address(request, self.config.trusted_proxy_hops)}"
        retry_after = self.counter.check(key, limit)

        if retry_after is not None:
            seconds = max(1, int(retry_after) + 1)
            response = JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "Too many requests. This endpoint allows "
                        f"{limit.count} per {limit.seconds} seconds."
                    )
                },
                headers={
                    "Retry-After": str(seconds),
                    "RateLimit-Limit": str(limit.count),
                    "RateLimit-Remaining": "0",
                    "RateLimit-Reset": str(seconds),
                },
            )
            await response(scope, receive, send)
            return

        await self._pass_through(scope, receive, send, limit)

    async def _pass_through(
        self, scope: Scope, receive: Receive, send: Send, limit: Limit
    ) -> None:
        """Call the app, naming the budget on its response."""

        async def send_with_limit_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("RateLimit-Limit", str(limit.count))
                headers.setdefault("RateLimit-Policy", f"{limit.count};w={limit.seconds}")
            await send(message)

        await self.app(scope, receive, send_with_limit_headers)
