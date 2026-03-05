"""Search endpoint router."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from ...cache import SQLiteCache
from ...search import SearchProgress
from ...services import search_itineraries
from ..jobs import JobManager
from ..schemas import JobResponse, JobStatus, SearchRequest, SearchResultResponse
from ..schemas import SearchProgress as SearchProgressSchema

router = APIRouter()
job_manager = JobManager()


def _run_search(job_id: str, req: SearchRequest) -> list[dict[str, object]]:
    cache: SQLiteCache | None = None
    if not req.no_cache:
        cache = SQLiteCache(Path.cwd() / "ryanair_cache.db")

    job = job_manager.get_job(job_id)

    def on_progress(progress: SearchProgress) -> None:
        if job is not None:
            job_manager.push_progress(job, progress)

    itineraries = search_itineraries(
        origin=req.origin.upper(),
        destination=req.destination.upper(),
        connections=[c.upper() for c in req.connections],
        start_date=req.start,
        end_date=req.end,
        currency=req.currency,
        min_connection_minutes=req.min_connection_minutes,
        max_connection_hours=req.max_connection_hours,
        allow_overnight=req.allow_overnight,
        cache=cache,
        on_progress=on_progress,
    )

    return [it.to_dict() for it in itineraries]


@router.post("/search")
def post_search(req: SearchRequest) -> dict[str, str]:
    job = job_manager.create_job()
    job_manager.submit(job, _run_search, job.id, req)
    return {"job_id": job.id}


@router.get("/search/{job_id}", response_model=JobResponse)
def get_search_status(job_id: str) -> JobResponse:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    progress = None
    if job.progress is not None:
        progress = SearchProgressSchema(
            connection=job.progress.connection,
            current=job.progress.current,
            total=job.progress.total,
            message=job.progress.message,
        )

    return JobResponse(
        job_id=job.id,
        status=JobStatus(job.status),
        progress=progress,
        error=job.error,
    )


@router.get("/search/{job_id}/events")
async def get_search_events(job_id: str) -> EventSourceResponse:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():  # type: ignore[no-untyped-def]
        async for event in job_manager.subscribe_events(job_id):
            yield {
                "event": event["event"],
                "data": json.dumps(event["data"]),
            }

    return EventSourceResponse(event_generator())


@router.get("/search/{job_id}/result", response_model=SearchResultResponse)
def get_search_result(job_id: str) -> SearchResultResponse:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "completed":
        raise HTTPException(status_code=404, detail="Results not available yet")

    itineraries = job.result or []
    return SearchResultResponse(count=len(itineraries), itineraries=itineraries)


@router.delete("/search/{job_id}")
def delete_search(job_id: str) -> dict[str, str]:
    if not job_manager.cancel_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "cancelled"}
