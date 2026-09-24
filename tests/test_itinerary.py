"""Tests for itinerary builder."""

from datetime import datetime
from decimal import Decimal

from ryanair_flight_search.itinerary import ItineraryBuilder
from ryanair_flight_search.models import Flight


class TestItineraryBuilder:
    def setup_method(self):
        self.builder = ItineraryBuilder(
            min_connection_minutes=60,
            max_connection_hours=8,
            allow_overnight=False,
        )

    def test_valid_itinerary(self, sample_flight_a, sample_flight_b):
        results = self.builder.build_itineraries([sample_flight_a], [sample_flight_b], "BGY")
        assert len(results) == 1
        it = results[0]
        assert it.connection_airport == "BGY"
        assert it.connection_minutes == 120
        assert it.total_price == Decimal("79.98")
        assert it.total_duration_minutes == 420

    def test_too_short_connection(self, sample_flight_a, sample_flight_early):
        results = self.builder.build_itineraries([sample_flight_a], [sample_flight_early], "BGY")
        assert len(results) == 0

    def test_too_long_connection(self, sample_flight_a, sample_flight_b):
        builder = ItineraryBuilder(
            min_connection_minutes=60,
            max_connection_hours=1,  # max 1 hour, but connection is 2h
        )
        results = builder.build_itineraries([sample_flight_a], [sample_flight_b], "BGY")
        assert len(results) == 0

    def test_overnight_rejected_by_default(self, sample_flight_a, sample_flight_next_day):
        results = self.builder.build_itineraries([sample_flight_a], [sample_flight_next_day], "BGY")
        assert len(results) == 0

    def test_overnight_allowed(self, sample_flight_a, sample_flight_next_day):
        builder = ItineraryBuilder(
            min_connection_minutes=60,
            max_connection_hours=24,
            allow_overnight=True,
        )
        results = builder.build_itineraries([sample_flight_a], [sample_flight_next_day], "BGY")
        assert len(results) == 1

    def test_none_price_propagates(self, sample_flight_a, sample_flight_no_price):
        results = self.builder.build_itineraries([sample_flight_a], [sample_flight_no_price], "BGY")
        assert len(results) == 1
        assert results[0].total_price is None

    def test_multiple_combinations(self, sample_flight_a, sample_flight_b, sample_flight_no_price):
        results = self.builder.build_itineraries(
            [sample_flight_a],
            [sample_flight_b, sample_flight_no_price],
            "BGY",
        )
        assert len(results) == 2


ZONES = {"CRV": "Europe/Rome", "DUB": "Europe/Dublin", "BGY": "Europe/Rome", "SVQ": "Europe/Madrid"}


def _flight(origin: str, destination: str, departure: datetime, arrival: datetime) -> Flight:
    return Flight(origin, destination, "FR1", departure, arrival, Decimal("20"), "EUR")


class TestTimeZones:
    """Ryanair gives every time in the local clock of its own airport."""

    def test_total_duration_is_real_elapsed_time(self):
        # Dublin runs an hour behind Seville: 06:20 to 15:40 on the clocks is 8h20m.
        first = _flight("DUB", "BGY", datetime(2026, 3, 3, 6, 20), datetime(2026, 3, 3, 10, 5))
        second = _flight("BGY", "SVQ", datetime(2026, 3, 3, 13, 15), datetime(2026, 3, 3, 15, 40))
        builder = ItineraryBuilder(timezones=ZONES)

        [itinerary] = builder.build_itineraries([first], [second], "BGY")

        assert itinerary.total_duration_minutes == 8 * 60 + 20
        assert itinerary.connection_minutes == 3 * 60 + 10

    def test_layover_across_the_clock_change_counts_the_extra_hour(self):
        # Clocks go back at 03:00 on 25 Oct 2026, so 23:00 to 06:00 is eight hours.
        first = _flight("CRV", "BGY", datetime(2026, 10, 24, 21, 15), datetime(2026, 10, 24, 23, 0))
        second = _flight("BGY", "SVQ", datetime(2026, 10, 25, 6, 0), datetime(2026, 10, 25, 8, 35))
        builder = ItineraryBuilder(max_connection_hours=12, allow_overnight=True, timezones=ZONES)

        [itinerary] = builder.build_itineraries([first], [second], "BGY")

        assert itinerary.connection_minutes == 8 * 60

    def test_unknown_zone_falls_back_to_clock_times(self):
        first = _flight("DUB", "BGY", datetime(2026, 3, 3, 6, 20), datetime(2026, 3, 3, 10, 5))
        second = _flight("BGY", "SVQ", datetime(2026, 3, 3, 13, 15), datetime(2026, 3, 3, 15, 40))
        builder = ItineraryBuilder(timezones={"DUB": "Not/AZone"})

        [itinerary] = builder.build_itineraries([first], [second], "BGY")

        assert itinerary.total_duration_minutes == 9 * 60 + 20
