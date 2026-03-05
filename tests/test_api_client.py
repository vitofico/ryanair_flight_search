"""Tests for Ryanair API client."""

from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from ryanair_flight_search.api_client import RyanairAPIClient, parse_datetime
from ryanair_flight_search.exceptions import APIError


class TestParseDatetime:
    def test_iso_with_microseconds(self):
        result = parse_datetime("2026-03-10T08:00:00.000000")
        assert result == datetime(2026, 3, 10, 8, 0)

    def test_iso_without_microseconds(self):
        result = parse_datetime("2026-03-10T08:00:00")
        assert result == datetime(2026, 3, 10, 8, 0)

    def test_iso_with_z_suffix(self):
        result = parse_datetime("2026-03-10T08:00:00Z")
        assert result == datetime(2026, 3, 10, 8, 0)

    def test_space_separated(self):
        result = parse_datetime("2026-03-10 08:00:00")
        assert result == datetime(2026, 3, 10, 8, 0)

    def test_short_format(self):
        result = parse_datetime("2026-03-10 08:00")
        assert result == datetime(2026, 3, 10, 8, 0)

    def test_invalid_returns_none(self):
        assert parse_datetime("not-a-date") is None

    def test_empty_string_returns_none(self):
        assert parse_datetime("") is None


class TestParseFlights:
    def setup_method(self):
        self.client = RyanairAPIClient()

    def test_parse_valid_flight_data(self):
        data = {
            "trips": [
                {
                    "origin": "CRV",
                    "destination": "BGY",
                    "dates": [
                        {
                            "flights": [
                                {
                                    "time": [
                                        "2026-03-10T08:00:00.000",
                                        "2026-03-10T10:00:00.000",
                                    ],
                                    "flightNumber": "FR1234",
                                    "regularFare": {"fares": [{"type": "ADT", "amount": 29.99}]},
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        flights = self.client._parse_flights(data, "CRV", "BGY")
        assert len(flights) == 1
        assert flights[0].origin == "CRV"
        assert flights[0].destination == "BGY"
        assert flights[0].flight_number == "FR1234"
        assert flights[0].price == Decimal("29.99")

    def test_parse_flight_no_fare(self):
        data = {
            "trips": [
                {
                    "origin": "CRV",
                    "destination": "BGY",
                    "dates": [
                        {
                            "flights": [
                                {
                                    "time": [
                                        "2026-03-10T08:00:00.000",
                                        "2026-03-10T10:00:00.000",
                                    ],
                                    "flightNumber": "FR1234",
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        flights = self.client._parse_flights(data, "CRV", "BGY")
        assert len(flights) == 1
        assert flights[0].price is None

    def test_parse_skips_wrong_route(self):
        data = {
            "trips": [
                {
                    "origin": "STN",
                    "destination": "DUB",
                    "dates": [
                        {
                            "flights": [
                                {
                                    "time": [
                                        "2026-03-10T08:00:00.000",
                                        "2026-03-10T10:00:00.000",
                                    ],
                                    "flightNumber": "FR9999",
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        flights = self.client._parse_flights(data, "CRV", "BGY")
        assert len(flights) == 0

    def test_parse_empty_trips(self):
        flights = self.client._parse_flights({"trips": []}, "CRV", "BGY")
        assert flights == []

    def test_parse_missing_time(self):
        data = {
            "trips": [
                {
                    "origin": "CRV",
                    "destination": "BGY",
                    "dates": [
                        {
                            "flights": [
                                {
                                    "time": [None, None],
                                    "flightNumber": "FR1234",
                                }
                            ]
                        }
                    ],
                }
            ]
        }
        flights = self.client._parse_flights(data, "CRV", "BGY")
        assert len(flights) == 0


class TestAPIClientErrors:
    def test_get_available_dates_404_returns_empty(self):
        client = RyanairAPIClient()
        with patch.object(client, "_get", side_effect=APIError("Not found", status_code=404)):
            result = client.get_available_dates("XXX", "YYY")
            assert result == []

    def test_get_available_dates_500_raises(self):
        client = RyanairAPIClient()
        with (
            patch.object(client, "_get", side_effect=APIError("Server error", status_code=500)),
            pytest.raises(APIError),
        ):
            client.get_available_dates("CRV", "BGY")

    def test_get_destinations_404_returns_empty(self):
        client = RyanairAPIClient()
        with patch.object(client, "_get", side_effect=APIError("Not found", status_code=404)):
            result = client.get_destinations("XXX")
            assert result == []

    def test_get_flights_400_returns_empty(self):
        client = RyanairAPIClient()
        with patch.object(client, "_get", side_effect=APIError("Bad request", status_code=400)):
            result = client.get_flights("CRV", "BGY", date(2026, 3, 10))
            assert result == []

    def test_get_destinations_parses_routes(self):
        client = RyanairAPIClient()
        mock_data = [
            {"arrivalAirport": {"code": "BGY", "name": "Milan Bergamo"}},
            {"arrivalAirport": {"code": "STN", "name": "London Stansted"}},
        ]
        with patch.object(client, "_get", return_value=mock_data):
            result = client.get_destinations("CRV")
            assert result == ["BGY", "STN"]
