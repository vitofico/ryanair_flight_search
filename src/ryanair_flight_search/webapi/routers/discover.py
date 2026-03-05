"""Discovery endpoint router."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from ...cache import SQLiteCache
from ...services import discover_connections
from ..schemas import DiscoverRequest, DiscoverResponse

router = APIRouter()


@router.post("/discover", response_model=DiscoverResponse)
def post_discover(req: DiscoverRequest) -> DiscoverResponse:
    cache: SQLiteCache | None = None
    if not req.no_cache:
        cache = SQLiteCache(Path.cwd() / "ryanair_cache.db")

    connections = discover_connections(
        origin=req.origin.upper(),
        destination=req.destination.upper(),
        cache=cache,
    )

    return DiscoverResponse(
        origin=req.origin.upper(),
        destination=req.destination.upper(),
        connections=connections,
    )
