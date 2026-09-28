"""Itinerary builder for connecting flights."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import DEFAULT_MAX_CONNECTION_HOURS, DEFAULT_MIN_CONNECTION_MINUTES
from .models import Flight, Itinerary

logger = logging.getLogger(__name__)


class ItineraryBuilder:
    """Builds and filters connecting flight itineraries."""

    def __init__(
        self,
        min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
        max_connection_hours: int = DEFAULT_MAX_CONNECTION_HOURS,
        allow_overnight: bool = False,
        timezones: dict[str, str] | None = None,
    ) -> None:
        self.min_connection_minutes = min_connection_minutes
        self.max_connection_hours = max_connection_hours
        self.allow_overnight = allow_overnight
        self.zones = _load_zones(timezones or {})

    def build_itineraries(
        self,
        first_leg_flights: list[Flight],
        second_leg_flights: list[Flight],
        connection_airport: str,
    ) -> list[Itinerary]:
        """Build valid connecting itineraries from two lists of flights."""
        itineraries = []

        for first in first_leg_flights:
            for second in second_leg_flights:
                itinerary = self._try_build(first, second, connection_airport)
                if itinerary:
                    itineraries.append(itinerary)

        return itineraries

    def _try_build(
        self,
        first: Flight,
        second: Flight,
        connection_airport: str,
    ) -> Itinerary | None:
        connection_delta = self._utc(second.departure_datetime, second.origin) - self._utc(
            first.arrival_datetime, first.destination
        )
        connection_minutes = int(connection_delta.total_seconds() / 60)

        if connection_minutes < self.min_connection_minutes:
            return None

        max_connection_minutes = self.max_connection_hours * 60
        if connection_minutes > max_connection_minutes:
            return None

        if (
            not self.allow_overnight
            and first.arrival_datetime.date() != second.departure_datetime.date()
        ):
            return None

        total_delta = self._utc(second.arrival_datetime, second.destination) - self._utc(
            first.departure_datetime, first.origin
        )
        total_duration_minutes = int(total_delta.total_seconds() / 60)

        total_price = None
        if first.price is not None and second.price is not None:
            total_price = first.price + second.price

        return Itinerary(
            first_leg=first,
            second_leg=second,
            connection_airport=connection_airport,
            connection_minutes=connection_minutes,
            total_price=total_price,
            total_duration_minutes=total_duration_minutes,
        )

    def _utc(self, local: datetime, airport: str) -> datetime:
        """Ryanair times are local to each airport; one with no known zone is read as UTC."""
        return local.replace(tzinfo=self.zones.get(airport, UTC)).astimezone(UTC)


def _load_zones(timezones: dict[str, str]) -> dict[str, tzinfo]:
    zones: dict[str, tzinfo] = {}
    for airport, name in timezones.items():
        try:
            zones[airport] = ZoneInfo(name)
        except (ZoneInfoNotFoundError, ValueError):
            logger.warning(
                "Unknown time zone %r for %s; using its clock times as UTC", name, airport
            )
    return zones
