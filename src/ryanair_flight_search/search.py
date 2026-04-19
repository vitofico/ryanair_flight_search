"""Flight search orchestrator."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import date, timedelta

from .api_client import RyanairAPIClient
from .itinerary import ItineraryBuilder
from .models import Itinerary

logger = logging.getLogger(__name__)


@dataclass
class SearchProgress:
    connection: str
    current: int  # 1-based index
    total: int
    message: str


ProgressCallback = Callable[[SearchProgress], None]


class FlightSearcher:
    """Orchestrates the flight search process."""

    def __init__(
        self,
        client: RyanairAPIClient,
        builder: ItineraryBuilder,
    ) -> None:
        self.client = client
        self.builder = builder

    def search(
        self,
        origin: str,
        connections: list[str],
        destination: str,
        start_date: date,
        end_date: date,
        on_progress: ProgressCallback | None = None,
    ) -> list[Itinerary]:
        """Search for connecting flight itineraries."""
        all_itineraries: list[Itinerary] = []

        date_range = list(_date_range(start_date, end_date))

        logger.info(
            "Searching: %s -> [%s] -> %s",
            origin,
            ",".join(connections),
            destination,
        )
        logger.info("Date range: %s to %s (%d days)", start_date, end_date, len(date_range))

        for i, connection in enumerate(connections, 1):
            if on_progress:
                on_progress(
                    SearchProgress(
                        connection=connection,
                        current=i,
                        total=len(connections),
                        message=f"Processing {connection} ({i}/{len(connections)})...",
                    )
                )
            logger.info("Processing connection: %s", connection)
            itineraries = self._search_via_connection(
                origin=origin,
                connection=connection,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
            )
            all_itineraries.extend(itineraries)
            logger.info("  Found %d itineraries via %s", len(itineraries), connection)

        all_itineraries.sort(key=lambda x: x.sort_key)

        logger.info("Total itineraries found: %d", len(all_itineraries))

        return all_itineraries

    def _search_via_connection(
        self,
        origin: str,
        connection: str,
        destination: str,
        start_date: date,
        end_date: date,
    ) -> list[Itinerary]:
        logger.info("  Fetching flights for %s->%s...", origin, connection)
        first_leg_flights = self.client.get_flights(origin, connection, start_date, end_date)

        logger.info("  Fetching flights for %s->%s...", connection, destination)
        second_leg_flights = self.client.get_flights(connection, destination, start_date, end_date)

        logger.info(
            "  Fetched %d flights for first leg, %d for second leg",
            len(first_leg_flights),
            len(second_leg_flights),
        )

        return self.builder.build_itineraries(
            first_leg_flights=first_leg_flights,
            second_leg_flights=second_leg_flights,
            connection_airport=connection,
        )


def _date_range(start: date, end: date) -> Iterator[date]:
    """Generate dates in range [start, end] inclusive."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
