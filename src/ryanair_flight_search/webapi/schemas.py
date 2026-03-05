"""Pydantic models for the web API."""

from __future__ import annotations

import enum
from datetime import date

from pydantic import BaseModel


class DiscoverRequest(BaseModel):
    origin: str
    destination: str
    no_cache: bool = False


class DiscoverResponse(BaseModel):
    origin: str
    destination: str
    connections: list[str]


class SearchRequest(BaseModel):
    origin: str
    destination: str
    connections: list[str]
    start: date
    end: date
    currency: str = "EUR"
    min_connection_minutes: int = 60
    max_connection_hours: int = 8
    allow_overnight: bool = False
    no_cache: bool = False


class SearchProgress(BaseModel):
    connection: str
    current: int
    total: int
    message: str


class JobStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    progress: SearchProgress | None = None
    error: str | None = None


class ItineraryResponse(BaseModel):
    model_config = {"extra": "allow"}


class SearchResultResponse(BaseModel):
    count: int
    itineraries: list[dict[str, object]]
