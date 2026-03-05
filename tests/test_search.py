"""Tests for flight search orchestrator."""

from datetime import date
from unittest.mock import MagicMock

from ryanair_flight_search.itinerary import ItineraryBuilder
from ryanair_flight_search.search import FlightSearcher, _date_range


class TestDateRange:
    def test_single_day(self):
        dates = list(_date_range(date(2026, 3, 10), date(2026, 3, 10)))
        assert dates == [date(2026, 3, 10)]

    def test_multiple_days(self):
        dates = list(_date_range(date(2026, 3, 10), date(2026, 3, 12)))
        assert len(dates) == 3
        assert dates[0] == date(2026, 3, 10)
        assert dates[-1] == date(2026, 3, 12)

    def test_empty_when_start_after_end(self):
        dates = list(_date_range(date(2026, 3, 12), date(2026, 3, 10)))
        assert dates == []


class TestFlightSearcher:
    def test_search_combines_connections(self, sample_flight_a, sample_flight_b):
        mock_client = MagicMock()
        mock_client.get_available_dates.return_value = [date(2026, 3, 10)]
        mock_client.get_flights.side_effect = [
            [sample_flight_a],  # CRV -> BGY
            [sample_flight_b],  # BGY -> SVQ
        ]

        builder = ItineraryBuilder()
        searcher = FlightSearcher(client=mock_client, builder=builder)

        results = searcher.search(
            origin="CRV",
            connections=["BGY"],
            destination="SVQ",
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
        )

        assert len(results) == 1
        assert results[0].connection_airport == "BGY"

    def test_search_no_dates_returns_empty(self):
        mock_client = MagicMock()
        mock_client.get_available_dates.return_value = []

        builder = ItineraryBuilder()
        searcher = FlightSearcher(client=mock_client, builder=builder)

        results = searcher.search(
            origin="CRV",
            connections=["BGY"],
            destination="SVQ",
            start_date=date(2026, 3, 10),
            end_date=date(2026, 3, 10),
        )

        assert results == []
