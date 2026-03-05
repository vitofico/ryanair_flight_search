"""Data models for flights and itineraries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Flight:
    """Represents a single flight leg."""

    origin: str
    destination: str
    flight_number: str | None
    departure_datetime: datetime
    arrival_datetime: datetime
    price: Decimal | None
    currency: str

    def to_dict(self) -> dict[str, object]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "flight_number": self.flight_number,
            "departure_datetime": self.departure_datetime.isoformat(),
            "arrival_datetime": self.arrival_datetime.isoformat(),
            "price": str(self.price) if self.price is not None else None,
            "currency": self.currency,
        }


@dataclass
class Itinerary:
    """Represents a complete one-stop itinerary."""

    first_leg: Flight
    second_leg: Flight
    connection_airport: str
    connection_minutes: int
    total_price: Decimal | None
    total_duration_minutes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "first_leg": self.first_leg.to_dict(),
            "second_leg": self.second_leg.to_dict(),
            "connection_airport": self.connection_airport,
            "connection_minutes": self.connection_minutes,
            "total_price": str(self.total_price) if self.total_price is not None else None,
            "total_duration_minutes": self.total_duration_minutes,
        }

    @property
    def sort_key(self) -> tuple[tuple[int, Decimal], datetime, int]:
        """Sort key: price (asc, None last), arrival time (asc), duration (asc)."""
        price_key = (
            (0, self.total_price) if self.total_price is not None else (1, Decimal("999999"))
        )
        return (
            price_key,
            self.second_leg.arrival_datetime,
            self.total_duration_minutes,
        )
