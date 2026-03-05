"""Shared test fixtures."""

from datetime import datetime
from decimal import Decimal

import pytest

from ryanair_flight_search.models import Flight


@pytest.fixture
def sample_flight_a():
    """First leg: CRV -> BGY, departs 08:00, arrives 10:00."""
    return Flight(
        origin="CRV",
        destination="BGY",
        flight_number="FR1234",
        departure_datetime=datetime(2026, 3, 10, 8, 0),
        arrival_datetime=datetime(2026, 3, 10, 10, 0),
        price=Decimal("29.99"),
        currency="EUR",
    )


@pytest.fixture
def sample_flight_b():
    """Second leg: BGY -> SVQ, departs 12:00, arrives 15:00."""
    return Flight(
        origin="BGY",
        destination="SVQ",
        flight_number="FR5678",
        departure_datetime=datetime(2026, 3, 10, 12, 0),
        arrival_datetime=datetime(2026, 3, 10, 15, 0),
        price=Decimal("49.99"),
        currency="EUR",
    )


@pytest.fixture
def sample_flight_early():
    """Second leg too early for connection: departs 10:30."""
    return Flight(
        origin="BGY",
        destination="SVQ",
        flight_number="FR9999",
        departure_datetime=datetime(2026, 3, 10, 10, 30),
        arrival_datetime=datetime(2026, 3, 10, 13, 30),
        price=Decimal("39.99"),
        currency="EUR",
    )


@pytest.fixture
def sample_flight_next_day():
    """Second leg next day: departs 08:00 on March 11."""
    return Flight(
        origin="BGY",
        destination="SVQ",
        flight_number="FR1111",
        departure_datetime=datetime(2026, 3, 11, 8, 0),
        arrival_datetime=datetime(2026, 3, 11, 11, 0),
        price=Decimal("19.99"),
        currency="EUR",
    )


@pytest.fixture
def sample_flight_no_price():
    """Flight with no price."""
    return Flight(
        origin="BGY",
        destination="SVQ",
        flight_number="FR0000",
        departure_datetime=datetime(2026, 3, 10, 14, 0),
        arrival_datetime=datetime(2026, 3, 10, 17, 0),
        price=None,
        currency="EUR",
    )
