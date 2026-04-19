"""Ryanair API client with caching, retries, and rate limiting."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .cache import SQLiteCache
from .config import (
    AIRPORTS_ENDPOINT,
    AVAILABLE_DATES_ENDPOINT,
    BASE_URL,
    DEFAULT_CURRENCY,
    FARFND_ONEWAY_FARES_ENDPOINT,
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

    def get_airports(self) -> list[dict[str, str]]:
        """Get all active Ryanair airports with IATA code, name, and country."""
        url = BASE_URL + AIRPORTS_ENDPOINT

        try:
            data = self._get(url)
            if isinstance(data, list):
                return [
                    {
                        "code": a["code"],
                        "name": a.get("name", ""),
                        "city": (
                            a.get("city", {}).get("name", "")
                            if isinstance(a.get("city"), dict)
                            else ""
                        ),
                        "country": (
                            a.get("country", {}).get("name", "")
                            if isinstance(a.get("country"), dict)
                            else ""
                        ),
                    }
                    for a in data
                    if "code" in a
                ]
            return []
        except APIError:
            return []

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
                    except (ValueError, TypeError):
                        continue
            return dates

        except APIError as e:
            if e.status_code in (404, 409):
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

    def get_flights(
        self, origin: str, destination: str, date_from: date, date_to: date
    ) -> list[Flight]:
        """Get available flights for a route and date range via the farfnd API.

        Queries each day individually because the farfnd endpoint only returns
        the single cheapest fare across the entire date range.
        """
        url = BASE_URL + FARFND_ONEWAY_FARES_ENDPOINT
        flights: list[Flight] = []
        current = date_from
        while current <= date_to:
            day_str = current.strftime("%Y-%m-%d")
            params = {
                "departureAirportIataCode": origin.upper(),
                "arrivalAirportIataCode": destination.upper(),
                "outboundDepartureDateFrom": day_str,
                "outboundDepartureDateTo": day_str,
                "currency": self.currency,
            }
            try:
                data = self._get(url, params)
                flights.extend(self._parse_farfnd_fares(data))
            except APIError as e:
                if e.status_code not in (400, 404, 409):
                    raise
            current += timedelta(days=1)
        return flights

    def _parse_farfnd_fares(self, data: Any) -> list[Flight]:
        flights: list[Flight] = []
        for fare in data.get("fares", []):
            try:
                outbound = fare["outbound"]
                dep_dt = parse_datetime(outbound["departureDate"])
                arr_dt = parse_datetime(outbound["arrivalDate"])
                if not dep_dt or not arr_dt:
                    continue

                price_data = outbound.get("price")
                price = Decimal(str(price_data["value"])) if price_data else None
                currency = price_data["currencyCode"] if price_data else self.currency

                flights.append(
                    Flight(
                        origin=outbound["departureAirport"]["iataCode"],
                        destination=outbound["arrivalAirport"]["iataCode"],
                        flight_number=outbound.get("flightNumber"),
                        departure_datetime=dep_dt,
                        arrival_datetime=arr_dt,
                        price=price,
                        currency=currency,
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Error parsing farfnd fare: %s", e)
        return flights


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
