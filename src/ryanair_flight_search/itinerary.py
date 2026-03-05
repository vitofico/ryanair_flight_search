"""Itinerary builder for connecting flights."""

from __future__ import annotations

from .config import DEFAULT_MAX_CONNECTION_HOURS, DEFAULT_MIN_CONNECTION_MINUTES
from .models import Flight, Itinerary


class ItineraryBuilder:
    """Builds and filters connecting flight itineraries."""

    def __init__(
        self,
        min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
        max_connection_hours: int = DEFAULT_MAX_CONNECTION_HOURS,
        allow_overnight: bool = False,
    ) -> None:
        self.min_connection_minutes = min_connection_minutes
        self.max_connection_hours = max_connection_hours
        self.allow_overnight = allow_overnight

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
        connection_delta = second.departure_datetime - first.arrival_datetime
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

        total_delta = second.arrival_datetime - first.departure_datetime
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
