"""FastAPI application for Ryanair flight search web UI."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import airports, discover, search


def _find_frontend_dist() -> Path | None:
    """Find the frontend dist directory (dev or Docker)."""
    # Docker build copies into webapi/static/
    bundled = Path(__file__).resolve().parent / "static"
    if bundled.is_dir():
        return bundled
    # Dev mode: frontend/dist at repo root
    dev = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"
    if dev.is_dir():
        return dev
    return None


app = FastAPI(title="Ryanair Flight Search", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(airports.router, prefix="/api/v1")
app.include_router(discover.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")

_frontend_dist = _find_frontend_dist()
if _frontend_dist is not None:
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def _spa_fallback(path: str) -> FileResponse:
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")
        index = _frontend_dist / "index.html"  # type: ignore[operator]
        if index.exists():
            return FileResponse(index)
        raise HTTPException(status_code=404, detail="Not found")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Ryanair Flight Search Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    import uvicorn

    uvicorn.run(app, host=args.host, port=args.port)
