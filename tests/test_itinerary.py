"""Tests for itinerary builder."""

from decimal import Decimal

from ryanair_flight_search.itinerary import ItineraryBuilder


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
