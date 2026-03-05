"""Domain exceptions for Ryanair flight search."""

from __future__ import annotations


class RyanairSearchError(Exception):
    """Base exception for all ryanair-flight-search errors."""


class APIError(RyanairSearchError):
    """Error communicating with the Ryanair API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InvalidRouteError(RyanairSearchError):
    """The requested route does not exist."""


class CacheError(RyanairSearchError):
    """Error reading from or writing to the cache."""
