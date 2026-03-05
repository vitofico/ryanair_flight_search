"""Ryanair API client with caching, retries, and rate limiting."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import SQLiteCache
from .config import (
    AVAILABILITY_ENDPOINT,
    AVAILABLE_DATES_ENDPOINT,
    BASE_URL,
    DEFAULT_CURRENCY,
    RATE_LIMIT_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    ROUTES_ENDPOINT,
    USER_AGENT,
)
from .exceptions import APIError
from .models import Flight

logger = logging.getLogger(__name__)


class RyanairAPIClient:
    """Client for interacting with Ryanair APIs."""

    def __init__(
        self,
        currency: str = DEFAULT_CURRENCY,
        cache: SQLiteCache | None = None,
    ) -> None:
        self.currency = currency
        self.session = self._create_session()
        self.cache = cache
        self._last_request_time: float = 0

    def _create_session(self) -> requests.Session:
        session = requests.Session()

        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Accept-Language": "en-GB,en;q=0.9",
            }
        )

        return session

    def _rate_limit(self) -> None:
        elapsed = time.time() - self._last_request_time
        if elapsed < RATE_LIMIT_DELAY_SECONDS:
            time.sleep(RATE_LIMIT_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: dict[str, str] | None = None) -> Any:
        if self.cache:
            cached = self.cache.get(url, params)
            if cached is not None:
                return cached

        self._rate_limit()
        logger.debug("API call: %s", url)

        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            data = response.json()

            if self.cache:
                self.cache.set(url, params, data)

            return data

        except requests.exceptions.HTTPError as e:
            raise APIError(str(e), status_code=e.response.status_code) from e
        except requests.exceptions.RequestException as e:
            raise APIError(str(e)) from e

    def get_available_dates(self, origin: str, destination: str) -> list[date]:
        """Get available flight dates for a route."""
        url = BASE_URL + AVAILABLE_DATES_ENDPOINT.format(
            origin=origin.upper(), destination=destination.upper()
        )

        try:
            data = self._get(url)
            dates: list[date] = []

            if isinstance(data, list):
                for date_str in data:
                    try:
                        dates.append(datetime.strptime(date_str, "%Y-%m-%d").date())
                    except ValueError, TypeError:
                        continue
            return dates

        except APIError as e:
            if e.status_code == 404:
                return []
            raise

    def get_destinations(self, airport: str) -> list[str]:
        """Get all airports with direct routes from the given airport."""
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
        except APIError as e:
            if e.status_code == 404:
                return []
            raise

    def get_flights(self, origin: str, destination: str, date_out: date) -> list[Flight]:
        """Get available flights for a specific route and date."""
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
        except APIError as e:
            if e.status_code in (404, 400):
                return []
            raise

    def _parse_flights(self, data: Any, origin: str, destination: str) -> list[Flight]:
        flights = []

        try:
            for trip in data.get("trips", []):
                if (
                    trip.get("origin") != origin.upper()
                    or trip.get("destination") != destination.upper()
                ):
                    continue

                for trip_date in trip.get("dates", []):
                    for flight_data in trip_date.get("flights", []):
                        flight = self._parse_single_flight(flight_data, origin, destination)
                        if flight:
                            flights.append(flight)

        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Error parsing flight data: %s", e)

        return flights

    def _parse_single_flight(
        self, flight_data: Any, origin: str, destination: str
    ) -> Flight | None:
        try:
            departure_str = flight_data.get("time", [None, None])[0]
            arrival_str = flight_data.get("time", [None, None])[1]

            if not departure_str:
                departure_str = flight_data.get("timeUTC", [None, None])[0]
            if not arrival_str:
                arrival_str = flight_data.get("timeUTC", [None, None])[1]

            if not departure_str or not arrival_str:
                return None

            departure_dt = parse_datetime(departure_str)
            arrival_dt = parse_datetime(arrival_str)

            if not departure_dt or not arrival_dt:
                return None

            flight_number = flight_data.get("flightNumber")

            price = None
            regular_fare = flight_data.get("regularFare")
            if regular_fare:
                fares = regular_fare.get("fares", [])
                if fares:
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
            logger.warning("Error parsing flight: %s", e)
            return None


def parse_datetime(dt_str: str) -> datetime | None:
    """Parse datetime string from the Ryanair API."""
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
