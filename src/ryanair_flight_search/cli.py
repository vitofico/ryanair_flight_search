"""Command-line interface for Ryanair flight search."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime
from pathlib import Path

from .api_client import RyanairAPIClient
from .cache import SQLiteCache
from .config import (
    CONNECTIONS_FILENAME,
    DEFAULT_CONNECTIONS,
    DEFAULT_CURRENCY,
    DEFAULT_DESTINATION,
    DEFAULT_MAX_CONNECTION_HOURS,
    DEFAULT_MIN_CONNECTION_MINUTES,
    DEFAULT_ORIGIN,
)
from .exceptions import APIError
from .itinerary import ItineraryBuilder
from .output import output_json, output_table
from .search import FlightSearcher

logger = logging.getLogger(__name__)


def _connections_path() -> Path:
    return Path.cwd() / CONNECTIONS_FILENAME


def load_connections(origin: str, destination: str) -> list[str] | None:
    """Load previously discovered connections from the connections file."""
    path = _connections_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
        key = f"{origin}->{destination}"
        entry = data.get(key)
        if entry:
            result: list[str] = entry["connections"]
            return result
    except json.JSONDecodeError, KeyError:
        pass
    return None


def save_connections(origin: str, destination: str, connections: list[str]) -> None:
    """Save discovered connections to the connections file."""
    path = _connections_path()
    data = {}
    if path.exists():
        import contextlib

        with contextlib.suppress(json.JSONDecodeError):
            data = json.loads(path.read_text())

    key = f"{origin}->{destination}"
    data[key] = {
        "origin": origin,
        "destination": destination,
        "connections": sorted(connections),
        "discovered_at": datetime.now().isoformat(),
    }
    path.write_text(json.dumps(data, indent=2) + "\n")


def validate_date(date_str: str, name: str) -> date:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error("Invalid %s date format: %s. Use YYYY-MM-DD.", name, date_str)
        sys.exit(1)


def _build_cache(no_cache: bool) -> SQLiteCache | None:
    if no_cache:
        return None
    return SQLiteCache(Path.cwd() / "ryanair_cache.db")


def cmd_discover(args: argparse.Namespace) -> None:
    """Discover valid connection airports for a route."""
    origin = args.origin.upper()
    destination = args.destination.upper()

    cache = _build_cache(args.no_cache)
    client = RyanairAPIClient(cache=cache)

    logger.info("Discovering connections for %s -> ??? -> %s", origin, destination)
    logger.info("  Fetching routes from %s...", origin)
    from_origin = set(client.get_destinations(origin))
    logger.info(
        "    %d destinations: %s",
        len(from_origin),
        ", ".join(sorted(from_origin)),
    )

    logger.info("  Fetching routes from %s (reverse)...", destination)
    from_destination = set(client.get_destinations(destination))
    logger.info(
        "    %d destinations: %s",
        len(from_destination),
        ", ".join(sorted(from_destination)),
    )

    connections = sorted(from_origin & from_destination - {origin, destination})
    logger.info("Valid connections (%d): %s", len(connections), ", ".join(connections))

    save_connections(origin, destination, connections)
    logger.info("Saved to %s", _connections_path())


def cmd_search(args: argparse.Namespace) -> None:
    """Run the flight search."""
    start_date = validate_date(args.start, "start")
    end_date = validate_date(args.end, "end")

    if start_date > end_date:
        logger.error("Start date must be before or equal to end date.")
        sys.exit(1)

    origin = args.origin.upper()
    destination = args.destination.upper()

    # Resolve connections: explicit > discovered > fallback
    connections: list[str]
    if args.connections:
        connections = [c.strip().upper() for c in args.connections.split(",") if c.strip()]
    else:
        loaded = load_connections(origin, destination)
        if loaded:
            connections = loaded
            logger.info("Using discovered connections from %s", CONNECTIONS_FILENAME)
        elif DEFAULT_CONNECTIONS:
            connections = DEFAULT_CONNECTIONS
            logger.info(
                "No discovered connections found, using defaults: %s",
                ",".join(connections),
            )
        else:
            connections = []

    if not connections:
        logger.error("No connection airports available. Run 'discover' first.")
        sys.exit(1)

    cache = _build_cache(args.no_cache)
    client = RyanairAPIClient(currency=args.currency, cache=cache)

    builder = ItineraryBuilder(
        min_connection_minutes=args.min_connection_minutes,
        max_connection_hours=args.max_connection_hours,
        allow_overnight=args.allow_overnight,
    )

    searcher = FlightSearcher(client=client, builder=builder)

    try:
        itineraries = searcher.search(
            origin=origin,
            connections=connections,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
        )
    except APIError as e:
        logger.error("API request failed: %s", e)
        sys.exit(1)

    if args.output == "json":
        output_json(itineraries)
    else:
        output_table(itineraries)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search for connecting flights on Ryanair",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # -- discover --
    discover_parser = subparsers.add_parser(
        "discover",
        help="Discover valid connection airports for a route",
    )
    discover_parser.add_argument(
        "--origin",
        default=DEFAULT_ORIGIN,
        help=f"Origin airport IATA code (default: {DEFAULT_ORIGIN})",
    )
    discover_parser.add_argument(
        "--destination",
        default=DEFAULT_DESTINATION,
        help=f"Destination airport IATA code (default: {DEFAULT_DESTINATION})",
    )
    discover_parser.add_argument(
        "--no-cache", action="store_true", help="Disable API response caching"
    )
    discover_parser.add_argument("--debug", action="store_true", help="Enable debug output")

    # -- search --
    search_parser = subparsers.add_parser(
        "search",
        help="Search for connecting flight itineraries",
    )
    search_parser.add_argument(
        "--origin",
        default=DEFAULT_ORIGIN,
        help=f"Origin airport IATA code (default: {DEFAULT_ORIGIN})",
    )
    search_parser.add_argument(
        "--connections",
        default=None,
        help="Comma-separated connection airports (default: auto-load or built-in fallback)",
    )
    search_parser.add_argument(
        "--destination",
        default=DEFAULT_DESTINATION,
        help=f"Destination airport IATA code (default: {DEFAULT_DESTINATION})",
    )
    search_parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    search_parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    search_parser.add_argument(
        "--currency",
        default=DEFAULT_CURRENCY,
        help=f"Currency code (default: {DEFAULT_CURRENCY})",
    )
    search_parser.add_argument(
        "--min-connection-minutes",
        type=int,
        default=DEFAULT_MIN_CONNECTION_MINUTES,
        help=f"Minimum connection time in minutes (default: {DEFAULT_MIN_CONNECTION_MINUTES})",
    )
    search_parser.add_argument(
        "--max-connection-hours",
        type=int,
        default=DEFAULT_MAX_CONNECTION_HOURS,
        help=f"Maximum connection time in hours (default: {DEFAULT_MAX_CONNECTION_HOURS})",
    )
    search_parser.add_argument(
        "--allow-overnight",
        action="store_true",
        default=False,
        help="Allow overnight connections",
    )
    search_parser.add_argument(
        "--output",
        choices=["table", "json"],
        default="table",
        help="Output format (default: table)",
    )
    search_parser.add_argument(
        "--no-cache", action="store_true", help="Disable API response caching"
    )
    search_parser.add_argument("--debug", action="store_true", help="Enable debug output")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Main entry point."""
    args = parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s",
        stream=sys.stderr,
    )

    if args.command == "discover":
        cmd_discover(args)
    elif args.command == "search":
        cmd_search(args)
