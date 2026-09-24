"""Tests for the service layer shared by the CLI and web API."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from ryanair_flight_search.models import Flight
from ryanair_flight_search.services import search_itineraries


def test_search_itineraries_measures_duration_in_airport_time_zones():
    first = Flight(
        "DUB",
        "BGY",
        "FR1",
        datetime(2026, 3, 3, 6, 20),
        datetime(2026, 3, 3, 10, 5),
        Decimal("30"),
        "EUR",
    )
    second = Flight(
        "BGY",
        "SVQ",
        "FR2",
        datetime(2026, 3, 3, 13, 15),
        datetime(2026, 3, 3, 15, 40),
        Decimal("45"),
        "EUR",
    )
    with patch("ryanair_flight_search.services.RyanairAPIClient") as client_cls:
        client = client_cls.return_value
        client.get_airports.return_value = [
            {"code": "DUB", "timezone": "Europe/Dublin"},
            {"code": "BGY", "timezone": "Europe/Rome"},
            {"code": "SVQ", "timezone": "Europe/Madrid"},
        ]
        client.get_flights.side_effect = [[first], [second]]

        [itinerary] = search_itineraries("DUB", "SVQ", ["BGY"], date(2026, 3, 3), date(2026, 3, 3))

    assert itinerary.total_duration_minutes == 8 * 60 + 20
