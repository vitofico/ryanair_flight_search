"""Domain exceptions for Ryanair flight search."""

from __future__ import annotations


class ScaloError(Exception):
    """Base exception for all scalo errors."""


class APIError(ScaloError):
    """Error communicating with the Ryanair API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class InvalidRouteError(ScaloError):
    """The requested route does not exist."""


class CacheError(ScaloError):
    """Error reading from or writing to the cache."""
