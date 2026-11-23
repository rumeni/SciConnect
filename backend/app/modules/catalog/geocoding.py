"""Turning a written address into map coordinates.

Geocoding happens when an institution is written (the result is kept on the
record) and when a visitor names a place to search around. Nothing geocodes on
read, so browsing the catalog never depends on the external service.

A lookup that fails, times out or finds nothing is not an error for a write:
the institution is stored without coordinates and simply has no map.

Every lookup, from either path, goes through one `NominatimGeocoder`, which
keeps the app inside Nominatim's usage policy
(https://operations.osmfoundation.org/policies/nominatim/):

- **One global budget.** Outbound requests start at least
  `geocoding_min_interval_seconds` apart (1 s by default, the policy maximum),
  however many visitors ask at once. The per-client rate limit in
  `app.core.ratelimit` is separate and still applies on top.
- **Bounded waiting.** A caller waits for the next free slot only up to
  `geocoding_max_wait_seconds`. When the queue is longer than that, it gets
  `GeocodingUnavailable` straight away, so a burst cannot tie up the server's
  worker threads.
- **A result cache.** Found places are cached for days, "no match" answers for
  an hour; equivalent queries (case and spacing aside) share an entry.
  Failures are never cached.
- **Backing off.** A 429 or 503 from the service pauses every lookup for its
  `Retry-After` (or `geocoding_cooldown_seconds`).

All of this state lives in process memory. Production runs one API worker
(compose.prod.yaml), so the budget holds. Each extra worker process or
container gets its own budget and cache, multiplying the request rate: scaling
out needs a shared store, or a self-hosted or commercial geocoder whose limits
allow it (`APP_GEOCODING_URL`).
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# A Retry-After longer than this is treated as this long, so one bad header
# cannot switch geocoding off for days.
MAX_COOLDOWN_SECONDS = 3600.0
# What to suggest after a timeout or server error that named no wait.
_SOON = 60.0


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    label: str


class Geocoder(Protocol):
    def __call__(self, query: str) -> Location | None: ...


class GeocodingUnavailable(Exception):
    """The lookup was not attempted or did not complete; asking later may work.

    Distinct from None, which means the service answered and found nothing.
    `retry_after` is the number of seconds until asking again is worthwhile.
    """

    def __init__(self, message: str, retry_after: float) -> None:
        super().__init__(message)
        self.retry_after = max(retry_after, 0.0)


def address_query(
    address: str | None, city: str | None, country: str | None
) -> str | None:
    """The most specific address line available, or None when there is nothing to look up."""
    parts = [part.strip() for part in (address, city, country) if part and part.strip()]
    return ", ".join(parts) or None


def normalize_query(query: str) -> str:
    """The form a query is sent and cached under: single spaces, trimmed."""
    return " ".join(query.split())


def no_geocoder(query: str) -> Location | None:
    """Used when geocoding is switched off, so writes never reach the network."""
    return None


@dataclass
class _Cached:
    expires_at: float
    location: Location | None


class NominatimGeocoder:
    """Nominatim lookups under one shared request budget, with a result cache.

    Thread-safe: FastAPI runs sync endpoints on a thread pool, so concurrent
    requests call this from several threads. The clock, sleep and HTTP
    transport are injectable so tests never wait or reach the network.
    """

    def __init__(
        self,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._transport = transport
        self._lock = threading.Lock()
        self._cache: OrderedDict[str, _Cached] = OrderedDict()
        # The earliest moment the next outbound request may start.
        self._next_slot = 0.0
        self._paused_until = 0.0

    def reset(self) -> None:
        with self._lock:
            self._cache.clear()
            self._next_slot = 0.0
            self._paused_until = 0.0

    def __call__(self, query: str) -> Location | None:
        """Look the place up. None: not found. Raises GeocodingUnavailable."""
        query = normalize_query(query)
        key = query.casefold()
        if not key:
            return None

        cached = self._cached(key)
        if cached is not None:
            return cached.location

        self._wait_for_slot(query)
        location = self._fetch(query)
        self._store(key, location)
        return location

    # --- Cache ----------------------------------------------------------------

    def _cached(self, key: str) -> _Cached | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at <= self._clock():
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return entry

    def _store(self, key: str, location: Location | None) -> None:
        ttl = (
            settings.geocoding_cache_ttl_seconds
            if location is not None
            else settings.geocoding_negative_cache_ttl_seconds
        )
        if ttl <= 0 or settings.geocoding_cache_max_entries <= 0:
            return
        with self._lock:
            self._cache[key] = _Cached(self._clock() + ttl, location)
            self._cache.move_to_end(key)
            while len(self._cache) > settings.geocoding_cache_max_entries:
                self._cache.popitem(last=False)

    # --- Budget ---------------------------------------------------------------

    def _wait_for_slot(self, query: str) -> None:
        """Reserve the next request slot, sleeping until it comes.

        Slots are handed out in order under the lock, then each caller sleeps
        outside it, so requests start at least the minimum interval apart even
        when many threads arrive together.

        With geocoding_max_wait_seconds below geocoding_min_interval_seconds
        nobody ever queues: in a burst only the first caller gets through.
        """
        with self._lock:
            now = self._clock()
            self._raise_if_paused(query, now)
            slot = max(now, self._next_slot)
            wait = slot - now
            if wait > settings.geocoding_max_wait_seconds:
                logger.info("Geocoding %r skipped: %.1fs queue exceeds the wait limit", query, wait)
                raise GeocodingUnavailable(
                    "too many address lookups at once",
                    retry_after=wait - settings.geocoding_max_wait_seconds,
                )
            self._next_slot = slot + settings.geocoding_min_interval_seconds
        if wait > 0:
            self._sleep(wait)
            # The service may have asked us to back off while we slept.
            with self._lock:
                self._raise_if_paused(query, self._clock())

    def _raise_if_paused(self, query: str, now: float) -> None:
        if now < self._paused_until:
            logger.info("Geocoding %r skipped: the service asked us to back off", query)
            raise GeocodingUnavailable(
                "the geocoding service asked us to slow down",
                retry_after=self._paused_until - now,
            )

    def _back_off(self, response: httpx.Response) -> float:
        retry = _retry_after(response)
        seconds = settings.geocoding_cooldown_seconds if retry is None else retry
        seconds = min(max(seconds, 0.0), MAX_COOLDOWN_SECONDS)
        with self._lock:
            self._paused_until = max(self._paused_until, self._clock() + seconds)
        logger.warning(
            "Geocoding service answered %s; pausing lookups for %.0fs",
            response.status_code,
            seconds,
        )
        return seconds

    # --- Upstream -------------------------------------------------------------

    def _fetch(self, query: str) -> Location | None:
        try:
            with httpx.Client(transport=self._transport) as client:
                response = client.get(
                    settings.geocoding_url,
                    params={"q": query, "format": "jsonv2", "limit": 1},
                    headers={
                        "User-Agent": settings.geocoding_user_agent,
                        "Accept-Language": "en",
                    },
                    timeout=settings.geocoding_timeout_seconds,
                )
        except httpx.HTTPError as error:
            logger.warning("Geocoding %r failed: %s", query, error)
            raise GeocodingUnavailable(
                "the geocoding service did not answer", retry_after=_SOON
            ) from error

        if response.status_code in (429, 503):
            pause = self._back_off(response)
            raise GeocodingUnavailable("the geocoding service asked us to slow down", pause)
        if response.status_code in (400, 404):
            # The service rejected this query itself; asking again will not help.
            logger.info("Geocoding %r was rejected with %s", query, response.status_code)
            return None
        if response.is_error:
            logger.warning("Geocoding %r failed with %s", query, response.status_code)
            raise GeocodingUnavailable(
                f"the geocoding service answered {response.status_code}", retry_after=_SOON
            )
        try:
            matches = response.json()
        except ValueError as error:
            logger.warning("Geocoding %r returned unreadable JSON: %s", query, error)
            raise GeocodingUnavailable(
                "the geocoding service gave an unreadable answer", retry_after=_SOON
            ) from error

        return _first_location(query, matches)


def _first_location(query: str, matches: object) -> Location | None:
    # The service answers with a list of matches, but an error reply is an object
    # and a proxy may return something else entirely. Anything unexpected means
    # "could not place it", never a failed write.
    if not isinstance(matches, list) or not matches:
        logger.info("Geocoding %r found no usable match", query)
        return None

    match = matches[0]
    try:
        latitude = float(match["lat"])
        longitude = float(match["lon"])
        label = str(match.get("display_name") or query)
    except (KeyError, IndexError, TypeError, ValueError, AttributeError) as error:
        logger.warning("Geocoding %r returned an unusable match: %s", query, error)
        return None

    if not _on_earth(latitude, longitude):
        logger.warning(
            "Geocoding %r returned an off-world position: %s, %s", query, latitude, longitude
        )
        return None

    return Location(latitude=latitude, longitude=longitude, label=label)


def _retry_after(response: httpx.Response) -> float | None:
    """Seconds from a Retry-After header, in either of its two forms."""
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        when = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    return when.timestamp() - time.time()


def _on_earth(latitude: float, longitude: float) -> bool:
    """Coordinates the database will accept, and that mean something on a map."""
    return (
        math.isfinite(latitude)
        and math.isfinite(longitude)
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


# The one instance every request shares: its budget and cache are per process.
nominatim_geocoder = NominatimGeocoder()


def default_geocoder() -> Geocoder:
    return nominatim_geocoder if settings.geocoding_enabled else no_geocoder
