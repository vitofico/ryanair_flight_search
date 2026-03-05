"""Shared service functions for CLI and web API."""

from __future__ import annotations

import logging
from datetime import date

from .api_client import RyanairAPIClient
from .cache import SQLiteCache
from .config import DEFAULT_CURRENCY, DEFAULT_MAX_CONNECTION_HOURS, DEFAULT_MIN_CONNECTION_MINUTES
from .itinerary import ItineraryBuilder
from .models import Itinerary
from .search import FlightSearcher, ProgressCallback

logger = logging.getLogger(__name__)


def discover_connections(
    origin: str,
    destination: str,
    cache: SQLiteCache | None = None,
) -> list[str]:
    """Discover valid connection airports between origin and destination."""
    client = RyanairAPIClient(cache=cache)

    logger.info("Discovering connections for %s -> ??? -> %s", origin, destination)
    from_origin = set(client.get_destinations(origin))
    from_destination = set(client.get_destinations(destination))

    return sorted(from_origin & from_destination - {origin, destination})


def search_itineraries(
    origin: str,
    destination: str,
    connections: list[str],
    start_date: date,
    end_date: date,
    currency: str = DEFAULT_CURRENCY,
    min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
    max_connection_hours: int = DEFAULT_MAX_CONNECTION_HOURS,
    allow_overnight: bool = False,
    cache: SQLiteCache | None = None,
    on_progress: ProgressCallback | None = None,
) -> list[Itinerary]:
    """Search for connecting flight itineraries."""
    client = RyanairAPIClient(currency=currency, cache=cache)
    builder = ItineraryBuilder(
        min_connection_minutes=min_connection_minutes,
        max_connection_hours=max_connection_hours,
        allow_overnight=allow_overnight,
    )
    searcher = FlightSearcher(client=client, builder=builder)
    return searcher.search(
        origin=origin,
        connections=connections,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        on_progress=on_progress,
    )
