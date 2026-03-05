"""Airports endpoint router."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from ...api_client import RyanairAPIClient
from ...cache import SQLiteCache

router = APIRouter()


@router.get("/airports")
def get_airports() -> list[dict[str, str]]:
    cache = SQLiteCache(Path.cwd() / "ryanair_cache.db")
    client = RyanairAPIClient(cache=cache)
    return client.get_airports()
