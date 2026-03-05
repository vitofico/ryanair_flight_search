#!/usr/bin/env python3
"""
Ryanair Connecting Flight Search
=================================

A production-quality Python script that queries the Ryanair public APIs to find
one-stop connecting flights between airports.

Example usage:
    # Discover connection airports (run periodically)
    python ryanair_search.py discover
    python ryanair_search.py discover --origin STN --destination MAD

    # Search using discovered connections
    python ryanair_search.py search --start 2026-02-01 --end 2026-02-10

    # Override connections manually
    python ryanair_search.py search --connections BGY,CRL \\
        --start 2026-03-01 --end 2026-03-07 --output json

API endpoints used (unofficial Ryanair APIs):
    1) Available dates: GET /api/farfnd/v4/oneWayFares/{origin}/{dest}/availabilities
    2) Flight availability: GET /api/booking/v4/en-gb/availability

Author: AI Assistant
License: MIT
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
from decimal import Decimal
from pathlib import Path
from typing import Iterator
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# =============================================================================
# CONSTANTS
# =============================================================================

BASE_URL = "https://www.ryanair.com"
AVAILABLE_DATES_ENDPOINT = "/api/farfnd/v4/oneWayFares/{origin}/{destination}/availabilities"
AVAILABILITY_ENDPOINT = "/api/booking/v4/en-gb/availability"
ROUTES_ENDPOINT = "/api/views/locate/searchWidget/routes/en/airport/{iata}"

DEFAULT_ORIGIN = "CRV"
DEFAULT_CONNECTIONS = ["BLQ", "NRN", "BGY", "TRN", "TSF"]
DEFAULT_DESTINATION = "SVQ"
DEFAULT_CURRENCY = "EUR"
DEFAULT_MIN_CONNECTION_MINUTES = 90
DEFAULT_MAX_CONNECTION_HOURS = 8

CONNECTIONS_FILE = Path(__file__).parent / "connections.json"

REQUEST_TIMEOUT_SECONDS = 30
RATE_LIMIT_DELAY_SECONDS = 0.5  # Delay between API calls
CACHE_EXPIRY_HOURS = 6

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# =============================================================================
# DATA MODELS
# =============================================================================

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

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
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

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return {
            "first_leg": self.first_leg.to_dict(),
            "second_leg": self.second_leg.to_dict(),
            "connection_airport": self.connection_airport,
            "connection_minutes": self.connection_minutes,
            "total_price": str(self.total_price) if self.total_price is not None else None,
            "total_duration_minutes": self.total_duration_minutes,
        }

    @property
    def sort_key(self) -> tuple:
        """
        Sort key for ranking itineraries:
        1. Total price (ascending, None values last)
        2. Final arrival time (ascending)
        3. Total duration (ascending)
        """
        price_key = (0, self.total_price) if self.total_price is not None else (1, Decimal("999999"))
        return (
            price_key,
            self.second_leg.arrival_datetime,
            self.total_duration_minutes,
        )


# =============================================================================
# CACHE IMPLEMENTATION
# =============================================================================

class SQLiteCache:
    """Simple SQLite-based cache for API responses."""

    def __init__(self, db_path: Path, expiry_hours: int = CACHE_EXPIRY_HOURS):
        self.db_path = db_path
        self.expiry_hours = expiry_hours
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the cache database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON cache(created_at)")
            conn.commit()

    def _make_key(self, url: str, params: dict | None = None) -> str:
        """Generate a cache key from URL and parameters."""
        key_data = url
        if params:
            key_data += "?" + urlencode(sorted(params.items()))
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, url: str, params: dict | None = None) -> dict | None:
        """Get cached response if available and not expired."""
        key = self._make_key(url, params)
        expiry_threshold = time.time() - (self.expiry_hours * 3600)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value, created_at FROM cache WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()

            if row is None:
                return None

            value, created_at = row
            if created_at < expiry_threshold:
                # Expired, delete and return None
                conn.execute("DELETE FROM cache WHERE key = ?", (key,))
                conn.commit()
                return None

            return json.loads(value)

    def set(self, url: str, params: dict | None, value: dict) -> None:
        """Store response in cache."""
        key = self._make_key(url, params)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO cache (key, value, created_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(value), time.time())
            )
            conn.commit()

    def cleanup(self) -> int:
        """Remove expired entries. Returns count of deleted rows."""
        expiry_threshold = time.time() - (self.expiry_hours * 3600)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM cache WHERE created_at < ?",
                (expiry_threshold,)
            )
            conn.commit()
            return cursor.rowcount


# =============================================================================
# API CLIENT
# =============================================================================

class RyanairAPIClient:
    """Client for interacting with Ryanair APIs."""

    def __init__(
        self,
        currency: str = DEFAULT_CURRENCY,
        cache_path: Path | None = None,
        debug: bool = False,
    ):
        self.currency = currency
        self.debug = debug
        self.session = self._create_session()
        self.cache = SQLiteCache(cache_path) if cache_path else None
        self._last_request_time: float = 0

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Configure retries for transient errors
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        # Set default headers
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-GB,en;q=0.9",
        })

        return session

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY_SECONDS:
            time.sleep(RATE_LIMIT_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: dict | None = None) -> dict:
        """Make a GET request with caching and rate limiting."""
        # Check cache first
        if self.cache:
            cached = self.cache.get(url, params)
            if cached is not None:
                if self.debug:
                    print(f"  [CACHE HIT] {url}", file=sys.stderr)
                return cached

        # Rate limit
        self._rate_limit()

        if self.debug:
            print(f"  [API CALL] {url}", file=sys.stderr)

        try:
            response = self.session.get(
                url,
                params=params,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            data = response.json()

            # Cache the response
            if self.cache:
                self.cache.set(url, params, data)

            return data

        except requests.exceptions.RequestException as e:
            if self.debug:
                print(f"  [ERROR] Request failed: {e}", file=sys.stderr)
            raise

    def get_available_dates(self, origin: str, destination: str) -> list[date]:
        """
        Get available flight dates for a route.

        Returns:
            List of dates with available flights.
        """
        url = BASE_URL + AVAILABLE_DATES_ENDPOINT.format(
            origin=origin.upper(),
            destination=destination.upper()
        )

        try:
            data = self._get(url)
            dates = []

            # Parse the availability response
            # The API returns a list of date strings in YYYY-MM-DD format
            if isinstance(data, list):
                for date_str in data:
                    try:
                        dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
                    except (ValueError, TypeError):
                        continue
            return dates

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # No route exists
                return []
            raise

    def get_destinations(self, airport: str) -> list[str]:
        """
        Get all airports with direct routes from the given airport.

        Returns:
            List of IATA codes.
        """
        url = BASE_URL + ROUTES_ENDPOINT.format(iata=airport.upper())

        try:
            data = self._get(url)
            if isinstance(data, list):
                return [
                    route["arrivalAirport"]["code"]
                    for route in data
                    if "arrivalAirport" in route and "code" in route["arrivalAirport"]
                ]
            return []
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return []
            raise

    def get_flights(
        self,
        origin: str,
        destination: str,
        date_out: date,
    ) -> list[Flight]:
        """
        Get available flights for a specific route and date.

        Returns:
            List of Flight objects.
        """
        url = BASE_URL + AVAILABILITY_ENDPOINT
        params = {
            "Origin": origin.upper(),
            "Destination": destination.upper(),
            "DateOut": date_out.strftime("%Y-%m-%d"),
            "RoundTrip": "false",
            "IncludeConnectingFlights": "false",
            "ADT": "1",
            "TEEN": "0",
            "CHD": "0",
            "INF": "0",
            "Disc": "0",
            "promoCode": "",
            "ToUs": "AGREED",
            "FlexDaysBeforeOut": "0",
            "FlexDaysOut": "0",
            "FlexDaysBeforeIn": "0",
            "FlexDaysIn": "0",
        }

        try:
            data = self._get(url, params)
            return self._parse_flights(data, origin, destination)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (404, 400):
                return []
            raise

    def _parse_flights(self, data: dict, origin: str, destination: str) -> list[Flight]:
        """Parse the availability API response into Flight objects."""
        flights = []

        try:
            trips = data.get("trips", [])
            for trip in trips:
                if trip.get("origin") != origin.upper() or trip.get("destination") != destination.upper():
                    continue

                for trip_date in trip.get("dates", []):
                    for flight_data in trip_date.get("flights", []):
                        flight = self._parse_single_flight(flight_data, origin, destination)
                        if flight:
                            flights.append(flight)

        except (KeyError, TypeError, ValueError) as e:
            if self.debug:
                print(f"  [WARN] Error parsing flight data: {e}", file=sys.stderr)

        return flights

    def _parse_single_flight(self, flight_data: dict, origin: str, destination: str) -> Flight | None:
        """Parse a single flight from the API response."""
        try:
            # Parse times - use local times to match what Ryanair displays
            departure_str = flight_data.get("time", [None, None])[0]
            arrival_str = flight_data.get("time", [None, None])[1]

            # Fallback to UTC if local times not available
            if not departure_str:
                departure_str = flight_data.get("timeUTC", [None, None])[0]
            if not arrival_str:
                arrival_str = flight_data.get("timeUTC", [None, None])[1]

            if not departure_str or not arrival_str:
                return None

            # Parse datetime strings
            departure_dt = self._parse_datetime(departure_str)
            arrival_dt = self._parse_datetime(arrival_str)

            if not departure_dt or not arrival_dt:
                return None

            # Get flight number
            flight_number = flight_data.get("flightNumber")

            # Get price (lowest regular fare)
            price = None
            regular_fare = flight_data.get("regularFare")
            if regular_fare:
                fares = regular_fare.get("fares", [])
                if fares:
                    # Get the lowest published fare amount
                    amounts = [
                        Decimal(str(f.get("amount", 0)))
                        for f in fares
                        if f.get("amount") is not None
                    ]
                    if amounts:
                        price = min(amounts)

            return Flight(
                origin=origin.upper(),
                destination=destination.upper(),
                flight_number=flight_number,
                departure_datetime=departure_dt,
                arrival_datetime=arrival_dt,
                price=price,
                currency=self.currency,
            )

        except Exception as e:
            if self.debug:
                print(f"  [WARN] Error parsing flight: {e}", file=sys.stderr)
            return None

    @staticmethod
    def _parse_datetime(dt_str: str) -> datetime | None:
        """Parse datetime string from API."""
        # Remove trailing Z (UTC indicator) if present
        cleaned = dt_str.rstrip("Z")

        formats = [
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(cleaned[:26], fmt)
            except ValueError:
                continue
        return None


# =============================================================================
# ITINERARY BUILDER
# =============================================================================

class ItineraryBuilder:
    """Builds and filters connecting flight itineraries."""

    def __init__(
        self,
        min_connection_minutes: int = DEFAULT_MIN_CONNECTION_MINUTES,
        max_connection_hours: int = DEFAULT_MAX_CONNECTION_HOURS,
        allow_overnight: bool = False,
    ):
        self.min_connection_minutes = min_connection_minutes
        self.max_connection_hours = max_connection_hours
        self.allow_overnight = allow_overnight

    def build_itineraries(
        self,
        first_leg_flights: list[Flight],
        second_leg_flights: list[Flight],
        connection_airport: str,
    ) -> list[Itinerary]:
        """
        Build valid connecting itineraries from two lists of flights.

        Args:
            first_leg_flights: Flights from origin to connection
            second_leg_flights: Flights from connection to destination
            connection_airport: IATA code of the connection airport

        Returns:
            List of valid Itinerary objects
        """
        itineraries = []

        for first in first_leg_flights:
            for second in second_leg_flights:
                itinerary = self._try_build_itinerary(first, second, connection_airport)
                if itinerary:
                    itineraries.append(itinerary)

        return itineraries

    def _try_build_itinerary(
        self,
        first: Flight,
        second: Flight,
        connection_airport: str,
    ) -> Itinerary | None:
        """Try to build a valid itinerary from two flights."""
        # Calculate connection time
        connection_delta = second.departure_datetime - first.arrival_datetime
        connection_minutes = int(connection_delta.total_seconds() / 60)

        # Check minimum connection time
        if connection_minutes < self.min_connection_minutes:
            return None

        # Check maximum connection time
        max_connection_minutes = self.max_connection_hours * 60
        if connection_minutes > max_connection_minutes:
            return None

        # Check overnight constraint
        if not self.allow_overnight:
            if first.arrival_datetime.date() != second.departure_datetime.date():
                return None

        # Calculate total duration
        total_delta = second.arrival_datetime - first.departure_datetime
        total_duration_minutes = int(total_delta.total_seconds() / 60)

        # Calculate total price
        total_price = None
        if first.price is not None and second.price is not None:
            total_price = first.price + second.price

        return Itinerary(
            first_leg=first,
            second_leg=second,
            connection_airport=connection_airport,
            connection_minutes=connection_minutes,
            total_price=total_price,
            total_duration_minutes=total_duration_minutes,
        )


# =============================================================================
# SEARCH ORCHESTRATOR
# =============================================================================

class FlightSearcher:
    """Orchestrates the flight search process."""

    def __init__(
        self,
        client: RyanairAPIClient,
        builder: ItineraryBuilder,
        debug: bool = False,
    ):
        self.client = client
        self.builder = builder
        self.debug = debug

    def search(
        self,
        origin: str,
        connections: list[str],
        destination: str,
        start_date: date,
        end_date: date,
    ) -> list[Itinerary]:
        """
        Search for connecting flight itineraries.

        Args:
            origin: Origin airport IATA code
            connections: List of connection airport IATA codes
            destination: Destination airport IATA code
            start_date: Start of date range (inclusive)
            end_date: End of date range (inclusive)

        Returns:
            List of Itinerary objects, sorted by preference
        """
        all_itineraries = []

        # Generate date range
        date_range = list(self._date_range(start_date, end_date))

        print(f"Searching: {origin} -> [{','.join(connections)}] -> {destination}")
        print(f"Date range: {start_date} to {end_date} ({len(date_range)} days)")
        print()

        for connection in connections:
            print(f"Processing connection: {connection}")
            itineraries = self._search_via_connection(
                origin=origin,
                connection=connection,
                destination=destination,
                date_range=date_range,
            )
            all_itineraries.extend(itineraries)
            print(f"  Found {len(itineraries)} itineraries via {connection}")

        # Sort by preference
        all_itineraries.sort(key=lambda x: x.sort_key)

        print()
        print(f"Total itineraries found: {len(all_itineraries)}")

        return all_itineraries

    def _search_via_connection(
        self,
        origin: str,
        connection: str,
        destination: str,
        date_range: list[date],
    ) -> list[Itinerary]:
        """Search for itineraries via a specific connection airport."""
        # Get available dates for both legs
        print(f"  Fetching available dates for {origin}->{connection}...")
        origin_to_conn_dates = set(self.client.get_available_dates(origin, connection))

        print(f"  Fetching available dates for {connection}->{destination}...")
        conn_to_dest_dates = set(self.client.get_available_dates(connection, destination))

        # Intersect with requested date range
        date_range_set = set(date_range)
        origin_to_conn_dates &= date_range_set
        conn_to_dest_dates &= date_range_set

        if not origin_to_conn_dates or not conn_to_dest_dates:
            print(f"  No overlapping dates available")
            return []

        print(f"  Available dates: {len(origin_to_conn_dates)} for first leg, {len(conn_to_dest_dates)} for second leg")

        # Fetch flights for available dates
        first_leg_flights = []
        for d in sorted(origin_to_conn_dates):
            flights = self.client.get_flights(origin, connection, d)
            first_leg_flights.extend(flights)

        second_leg_flights = []
        for d in sorted(conn_to_dest_dates):
            flights = self.client.get_flights(connection, destination, d)
            second_leg_flights.extend(flights)

        print(f"  Fetched {len(first_leg_flights)} flights for first leg, {len(second_leg_flights)} for second leg")

        # Build itineraries
        itineraries = self.builder.build_itineraries(
            first_leg_flights=first_leg_flights,
            second_leg_flights=second_leg_flights,
            connection_airport=connection,
        )

        return itineraries

    @staticmethod
    def _date_range(start: date, end: date) -> Iterator[date]:
        """Generate dates in range [start, end] inclusive."""
        current = start
        while current <= end:
            yield current
            current += timedelta(days=1)


# =============================================================================
# OUTPUT FORMATTERS
# =============================================================================

def format_duration(minutes: int) -> str:
    """Format duration in minutes as 'Xh Ym'."""
    hours, mins = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def format_price(price: Decimal | None, currency: str) -> str:
    """Format price with currency."""
    if price is None:
        return "N/A"
    return f"{currency} {price:.2f}"


def output_table(itineraries: list[Itinerary]) -> None:
    """Output itineraries as a formatted table."""
    if not itineraries:
        print("No itineraries found.")
        return

    # Table header
    print()
    print("=" * 120)
    print(f"{'#':>3} | {'First Leg':<30} | {'Connection':<12} | {'Second Leg':<30} | {'Total':>10} | {'Duration':>10}")
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

        print(f"{i:>3} | {first_leg:<30} | {connection:<12} | {second_leg:<30} | {total_price:>10} | {duration:>10}")

    print("=" * 120)
    print(f"Total: {len(itineraries)} itineraries")


def output_json(itineraries: list[Itinerary]) -> None:
    """Output itineraries as JSON."""
    data = {
        "count": len(itineraries),
        "itineraries": [it.to_dict() for it in itineraries],
    }
    print(json.dumps(data, indent=2))


# =============================================================================
# CLI
# =============================================================================

def load_connections(origin: str, destination: str) -> list[str] | None:
    """Load previously discovered connections from the connections file."""
    if not CONNECTIONS_FILE.exists():
        return None
    try:
        data = json.loads(CONNECTIONS_FILE.read_text())
        key = f"{origin}->{destination}"
        entry = data.get(key)
        if entry:
            return entry["connections"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def save_connections(origin: str, destination: str, connections: list[str]) -> None:
    """Save discovered connections to the connections file."""
    data = {}
    if CONNECTIONS_FILE.exists():
        try:
            data = json.loads(CONNECTIONS_FILE.read_text())
        except json.JSONDecodeError:
            pass

    key = f"{origin}->{destination}"
    data[key] = {
        "origin": origin,
        "destination": destination,
        "connections": sorted(connections),
        "discovered_at": datetime.now().isoformat(),
    }
    CONNECTIONS_FILE.write_text(json.dumps(data, indent=2) + "\n")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Search for connecting flights on Ryanair",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- discover subcommand --
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover valid connection airports for a route",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Discover connections for default route
  python ryanair_search.py discover

  # Discover connections for a custom route
  python ryanair_search.py discover --origin STN --destination MAD
        """,
    )
    discover_parser.add_argument(
        "--origin", default=DEFAULT_ORIGIN,
        help=f"Origin airport IATA code (default: {DEFAULT_ORIGIN})",
    )
    discover_parser.add_argument(
        "--destination", default=DEFAULT_DESTINATION,
        help=f"Destination airport IATA code (default: {DEFAULT_DESTINATION})",
    )
    discover_parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable caching of API responses",
    )
    discover_parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug output",
    )

    # -- search subcommand --
    search_parser = subparsers.add_parser(
        "search",
        help="Search for connecting flight itineraries",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using defaults (auto-loads discovered connections)
  python ryanair_search.py search --start 2026-02-01 --end 2026-02-10

  # Override connections manually
  python ryanair_search.py search --connections BGY,CRL \\
      --start 2026-03-01 --end 2026-03-07 --output json
        """,
    )
    search_parser.add_argument(
        "--origin", default=DEFAULT_ORIGIN,
        help=f"Origin airport IATA code (default: {DEFAULT_ORIGIN})",
    )
    search_parser.add_argument(
        "--connections", default=None,
        help="Comma-separated connection airports (default: auto-load from discover, or built-in fallback)",
    )
    search_parser.add_argument(
        "--destination", default=DEFAULT_DESTINATION,
        help=f"Destination airport IATA code (default: {DEFAULT_DESTINATION})",
    )
    search_parser.add_argument(
        "--start", required=True,
        help="Start date (YYYY-MM-DD)",
    )
    search_parser.add_argument(
        "--end", required=True,
        help="End date (YYYY-MM-DD)",
    )
    search_parser.add_argument(
        "--currency", default=DEFAULT_CURRENCY,
        help=f"Currency code (default: {DEFAULT_CURRENCY})",
    )
    search_parser.add_argument(
        "--min-connection-minutes", type=int, default=DEFAULT_MIN_CONNECTION_MINUTES,
        help=f"Minimum connection time in minutes (default: {DEFAULT_MIN_CONNECTION_MINUTES})",
    )
    search_parser.add_argument(
        "--max-connection-hours", type=int, default=DEFAULT_MAX_CONNECTION_HOURS,
        help=f"Maximum connection time in hours (default: {DEFAULT_MAX_CONNECTION_HOURS})",
    )
    search_parser.add_argument(
        "--allow-overnight", action="store_true", default=False,
        help="Allow overnight connections (default: false)",
    )
    search_parser.add_argument(
        "--output", choices=["table", "json"], default="table",
        help="Output format (default: table)",
    )
    search_parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable caching of API responses",
    )
    search_parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug output",
    )

    return parser.parse_args()


def validate_date(date_str: str, name: str) -> date:
    """Validate and parse a date string."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid {name} date format: {date_str}. Use YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover valid connection airports for a route."""
    origin = args.origin.upper()
    destination = args.destination.upper()

    cache_path = None
    if not args.no_cache:
        cache_path = Path(__file__).parent / "ryanair_cache.db"

    client = RyanairAPIClient(cache_path=cache_path, debug=args.debug)

    print(f"Discovering connections for {origin} -> ??? -> {destination}")
    print(f"  Fetching routes from {origin}...")
    from_origin = set(client.get_destinations(origin))
    print(f"    {len(from_origin)} destinations: {', '.join(sorted(from_origin))}")

    print(f"  Fetching routes from {destination} (reverse)...")
    from_destination = set(client.get_destinations(destination))
    print(f"    {len(from_destination)} destinations: {', '.join(sorted(from_destination))}")

    connections = sorted(from_origin & from_destination - {origin, destination})
    print()
    print(f"Valid connections ({len(connections)}): {', '.join(connections)}")

    save_connections(origin, destination, connections)
    print(f"Saved to {CONNECTIONS_FILE}")


def cmd_search(args: argparse.Namespace) -> None:
    """Run the flight search."""
    start_date = validate_date(args.start, "start")
    end_date = validate_date(args.end, "end")

    if start_date > end_date:
        print("Error: Start date must be before or equal to end date.", file=sys.stderr)
        sys.exit(1)

    origin = args.origin.upper()
    destination = args.destination.upper()

    # Resolve connections: explicit > discovered > fallback
    if args.connections:
        connections = [c.strip().upper() for c in args.connections.split(",") if c.strip()]
    else:
        connections = load_connections(origin, destination)
        if connections:
            print(f"Using discovered connections from {CONNECTIONS_FILE.name}")
        else:
            connections = DEFAULT_CONNECTIONS
            print(f"No discovered connections found, using defaults: {','.join(connections)}")

    if not connections:
        print("Error: No connection airports available. Run 'discover' first.", file=sys.stderr)
        sys.exit(1)

    cache_path = None
    if not args.no_cache:
        cache_path = Path(__file__).parent / "ryanair_cache.db"

    client = RyanairAPIClient(
        currency=args.currency,
        cache_path=cache_path,
        debug=args.debug,
    )

    builder = ItineraryBuilder(
        min_connection_minutes=args.min_connection_minutes,
        max_connection_hours=args.max_connection_hours,
        allow_overnight=args.allow_overnight,
    )

    searcher = FlightSearcher(
        client=client,
        builder=builder,
        debug=args.debug,
    )

    try:
        itineraries = searcher.search(
            origin=origin,
            connections=connections,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
        )
    except requests.exceptions.RequestException as e:
        print(f"Error: API request failed: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            raise
        sys.exit(1)

    if args.output == "json":
        output_json(itineraries)
    else:
        output_table(itineraries)


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "search":
        cmd_search(args)


if __name__ == "__main__":
    main()
