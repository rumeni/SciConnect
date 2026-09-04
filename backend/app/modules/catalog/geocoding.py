"""Turning a written address into map coordinates.

Geocoding happens once, when an institution is written, and the result is kept
on the record. Nothing geocodes on read, so browsing the catalog never depends
on the external service being reachable.

A lookup that fails, times out or finds nothing is not an error: the
institution is stored without coordinates and simply has no map.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Location:
    latitude: float
    longitude: float
    label: str


class Geocoder(Protocol):
    def __call__(self, query: str) -> Location | None: ...


def address_query(
    address: str | None, city: str | None, country: str | None
) -> str | None:
    """The most specific address line available, or None when there is nothing to look up."""
    parts = [part.strip() for part in (address, city, country) if part and part.strip()]
    return ", ".join(parts) or None


def no_geocoder(query: str) -> Location | None:
    """Used when geocoding is switched off, so writes never reach the network."""
    return None


def nominatim_geocoder(query: str) -> Location | None:
    """Look the address up with OpenStreetMap's Nominatim service."""
    try:
        response = httpx.get(
            settings.geocoding_url,
            params={"q": query, "format": "jsonv2", "limit": 1},
            headers={
                "User-Agent": settings.geocoding_user_agent,
                "Accept-Language": "en",
            },
            timeout=settings.geocoding_timeout_seconds,
        )
        response.raise_for_status()
        matches = response.json()
    except (httpx.HTTPError, ValueError) as error:
        logger.warning("Geocoding %r failed: %s", query, error)
        return None

    if not matches:
        logger.info("Geocoding %r found no match", query)
        return None

    match = matches[0]
    try:
        return Location(
            latitude=float(match["lat"]),
            longitude=float(match["lon"]),
            label=match.get("display_name", query),
        )
    except (KeyError, TypeError, ValueError) as error:
        logger.warning("Geocoding %r returned an unusable match: %s", query, error)
        return None


def default_geocoder() -> Geocoder:
    return nominatim_geocoder if settings.geocoding_enabled else no_geocoder
