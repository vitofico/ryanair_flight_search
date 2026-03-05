"""Tests for data models."""

from decimal import Decimal

from ryanair_flight_search.models import Itinerary


class TestFlight:
    def test_to_dict(self, sample_flight_a):
        d = sample_flight_a.to_dict()
        assert d["origin"] == "CRV"
        assert d["destination"] == "BGY"
        assert d["flight_number"] == "FR1234"
        assert d["departure_datetime"] == "2026-03-10T08:00:00"
        assert d["arrival_datetime"] == "2026-03-10T10:00:00"
        assert d["price"] == "29.99"
        assert d["currency"] == "EUR"

    def test_to_dict_none_price(self, sample_flight_no_price):
        d = sample_flight_no_price.to_dict()
        assert d["price"] is None


class TestItinerary:
    def test_to_dict(self, sample_flight_a, sample_flight_b):
        it = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("79.98"),
            total_duration_minutes=420,
        )
        d = it.to_dict()
        assert d["connection_airport"] == "BGY"
        assert d["connection_minutes"] == 120
        assert d["total_price"] == "79.98"
        assert d["total_duration_minutes"] == 420
        assert d["first_leg"]["origin"] == "CRV"
        assert d["second_leg"]["destination"] == "SVQ"

    def test_sort_key_by_price(self, sample_flight_a, sample_flight_b):
        cheap = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("50.00"),
            total_duration_minutes=420,
        )
        expensive = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("150.00"),
            total_duration_minutes=420,
        )
        assert cheap.sort_key < expensive.sort_key

    def test_sort_key_none_price_last(self, sample_flight_a, sample_flight_b):
        priced = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("999.00"),
            total_duration_minutes=420,
        )
        no_price = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=None,
            total_duration_minutes=420,
        )
        assert priced.sort_key < no_price.sort_key
