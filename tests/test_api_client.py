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


class TestParseFarfndFares:
    def setup_method(self):
        self.client = RyanairAPIClient()

    def test_parse_valid_fare(self):
        data = {
            "fares": [
                {
                    "outbound": {
                        "departureAirport": {"iataCode": "CRV"},
                        "arrivalAirport": {"iataCode": "BGY"},
                        "departureDate": "2026-03-10T08:00:00",
                        "arrivalDate": "2026-03-10T10:00:00",
                        "flightNumber": "FR1234",
                        "price": {"value": 29.99, "currencyCode": "EUR"},
                    }
                }
            ]
        }
        flights = self.client._parse_farfnd_fares(data)
        assert len(flights) == 1
        assert flights[0].origin == "CRV"
        assert flights[0].destination == "BGY"
        assert flights[0].flight_number == "FR1234"
        assert flights[0].price == Decimal("29.99")
        assert flights[0].currency == "EUR"

    def test_parse_no_price(self):
        data = {
            "fares": [
                {
                    "outbound": {
                        "departureAirport": {"iataCode": "CRV"},
                        "arrivalAirport": {"iataCode": "BGY"},
                        "departureDate": "2026-03-10T08:00:00",
                        "arrivalDate": "2026-03-10T10:00:00",
                        "flightNumber": "FR1234",
                    }
                }
            ]
        }
        flights = self.client._parse_farfnd_fares(data)
        assert len(flights) == 1
        assert flights[0].price is None

    def test_parse_empty_fares(self):
        flights = self.client._parse_farfnd_fares({"fares": []})
        assert flights == []

    def test_parse_skips_invalid_dates(self):
        data = {
            "fares": [
                {
                    "outbound": {
                        "departureAirport": {"iataCode": "CRV"},
                        "arrivalAirport": {"iataCode": "BGY"},
                        "departureDate": "bad-date",
                        "arrivalDate": "bad-date",
                        "flightNumber": "FR1234",
                        "price": {"value": 29.99, "currencyCode": "EUR"},
                    }
                }
            ]
        }
        flights = self.client._parse_farfnd_fares(data)
        assert len(flights) == 0


def _fare(departure: str, arrival: str, number: str, price: float) -> dict:
    return {
        "outbound": {
            "departureAirport": {"iataCode": "BGY"},
            "arrivalAirport": {"iataCode": "SVQ"},
            "departureDate": departure,
            "arrivalDate": arrival,
            "flightNumber": number,
            "price": {"value": price, "currencyCode": "EUR"},
        }
    }


class TestGetFlights:
    def test_returns_every_scheduled_flight_not_just_the_cheapest(self):
        """farfnd answers any query with its single cheapest fare, so each
        scheduled departure has to be priced on its own."""
        timetable = {
            "month": 11,
            "days": [
                {
                    "day": 1,
                    "flights": [
                        {"number": "76", "departureTime": "06:00", "arrivalTime": "08:35"},
                        {"number": "1296", "departureTime": "15:30", "arrivalTime": "18:05"},
                    ],
                },
                {
                    "day": 3,
                    "flights": [
                        {"number": "76", "departureTime": "06:00", "arrivalTime": "08:35"},
                    ],
                },
            ],
        }
        fares = {
            ("2026-11-01", "06:00"): _fare(
                "2026-11-01T06:00:00", "2026-11-01T08:35:00", "FR76", 22.52
            ),
            ("2026-11-01", "15:30"): _fare(
                "2026-11-01T15:30:00", "2026-11-01T18:05:00", "FR1296", 38.66
            ),
        }

        def fake_get(url, params=None):
            if "/timtbl/" in url:
                assert url.endswith("/schedules/BGY/SVQ/years/2026/months/11")
                return timetable
            window = params["outboundDepartureTimeFrom"]
            assert params["outboundDepartureTimeTo"] == window
            assert params["outboundDepartureDateFrom"] == params["outboundDepartureDateTo"]
            fare = fares.get((params["outboundDepartureDateFrom"], window))
            return {"fares": [fare] if fare else []}

        client = RyanairAPIClient()
        with patch.object(client, "_get", side_effect=fake_get):
            flights = client.get_flights("BGY", "SVQ", date(2026, 11, 1), date(2026, 11, 2))

        assert [(f.flight_number, f.departure_datetime) for f in flights] == [
            ("FR76", datetime(2026, 11, 1, 6, 0)),
            ("FR1296", datetime(2026, 11, 1, 15, 30)),
        ]

    def test_reads_every_month_the_range_spans(self):
        client = RyanairAPIClient()
        with patch.object(client, "_get", return_value={"days": []}) as get:
            client.get_flights("CRV", "BGY", date(2026, 12, 20), date(2027, 1, 10))

        urls = [c.args[0] for c in get.call_args_list]
        assert [u.rsplit("/years/", 1)[1] for u in urls] == ["2026/months/12", "2027/months/1"]


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
            result = client.get_flights("CRV", "BGY", date(2026, 3, 10), date(2026, 3, 15))
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
