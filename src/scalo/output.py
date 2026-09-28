"""Output formatters for flight itineraries."""

from __future__ import annotations

import json
from decimal import Decimal

from .models import Itinerary


def format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def format_price(price: Decimal | None, currency: str) -> str:
    if price is None:
        return "N/A"
    return f"{currency} {price:.2f}"


def output_table(itineraries: list[Itinerary]) -> None:
    """Print itineraries as a formatted table to stdout."""
    if not itineraries:
        print("No itineraries found.")
        return

    print()
    print("=" * 120)
    print(
        f"{'#':>3} | {'First Leg':<30} | {'Connection':<12} | "
        f"{'Second Leg':<30} | {'Total':>10} | {'Duration':>10}"
    )
    print("-" * 120)

    for i, it in enumerate(itineraries, 1):
        first_leg = (
            f"{it.first_leg.origin}->{it.first_leg.destination} "
            f"{it.first_leg.departure_datetime.strftime('%m/%d %H:%M')}-"
            f"{it.first_leg.arrival_datetime.strftime('%H:%M')}"
        )
        second_leg = (
            f"{it.second_leg.origin}->{it.second_leg.destination} "
            f"{it.second_leg.departure_datetime.strftime('%m/%d %H:%M')}-"
            f"{it.second_leg.arrival_datetime.strftime('%H:%M')}"
        )
        connection = f"{it.connection_airport} ({format_duration(it.connection_minutes)})"
        total_price = format_price(it.total_price, it.first_leg.currency)
        duration = format_duration(it.total_duration_minutes)

        print(
            f"{i:>3} | {first_leg:<30} | {connection:<12} | "
            f"{second_leg:<30} | {total_price:>10} | {duration:>10}"
        )

    print("=" * 120)
    print(f"Total: {len(itineraries)} itineraries")


def output_json(itineraries: list[Itinerary]) -> None:
    """Print itineraries as JSON to stdout."""
    data = {
        "count": len(itineraries),
        "itineraries": [it.to_dict() for it in itineraries],
    }
    print(json.dumps(data, indent=2))
