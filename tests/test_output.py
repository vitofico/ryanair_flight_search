"""Tests for output formatters."""

import json
from decimal import Decimal

from ryanair_flight_search.models import Itinerary
from ryanair_flight_search.output import (
    format_duration,
    format_price,
    output_json,
    output_table,
)


class TestFormatDuration:
    def test_minutes_only(self):
        assert format_duration(45) == "45m"

    def test_hours_and_minutes(self):
        assert format_duration(130) == "2h 10m"

    def test_exact_hours(self):
        assert format_duration(120) == "2h 0m"

    def test_zero(self):
        assert format_duration(0) == "0m"


class TestFormatPrice:
    def test_with_price(self):
        assert format_price(Decimal("29.99"), "EUR") == "EUR 29.99"

    def test_none_price(self):
        assert format_price(None, "EUR") == "N/A"

    def test_zero_price(self):
        assert format_price(Decimal("0"), "EUR") == "EUR 0.00"


class TestOutputTable:
    def test_empty_itineraries(self, capsys):
        output_table([])
        captured = capsys.readouterr()
        assert "No itineraries found" in captured.out

    def test_with_itineraries(self, capsys, sample_flight_a, sample_flight_b):
        it = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("79.98"),
            total_duration_minutes=420,
        )
        output_table([it])
        captured = capsys.readouterr()
        assert "CRV->BGY" in captured.out
        assert "BGY->SVQ" in captured.out
        assert "79.98" in captured.out
        assert "Total: 1 itineraries" in captured.out


class TestOutputJson:
    def test_empty(self, capsys):
        output_json([])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["count"] == 0
        assert data["itineraries"] == []

    def test_with_itineraries(self, capsys, sample_flight_a, sample_flight_b):
        it = Itinerary(
            first_leg=sample_flight_a,
            second_leg=sample_flight_b,
            connection_airport="BGY",
            connection_minutes=120,
            total_price=Decimal("79.98"),
            total_duration_minutes=420,
        )
        output_json([it])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["count"] == 1
        assert data["itineraries"][0]["connection_airport"] == "BGY"
