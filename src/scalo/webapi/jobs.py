"""In-memory job manager for background search tasks."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any

from ..search import SearchProgress

logger = logging.getLogger(__name__)


@dataclass
class Job:
    id: str
    status: str = "queued"
    progress: SearchProgress | None = None
    result: list[dict[str, object]] | None = None
    error: str | None = None
    cancel_event: threading.Event = field(default_factory=threading.Event)
    _event_queue: Queue[dict[str, Any]] = field(default_factory=Queue)


class JobManager:
    def __init__(self, max_workers: int = 2) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def create_job(self) -> Job:
        job = Job(id=str(uuid.uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job is None:
            return False
        job.cancel_event.set()
        return True

    def submit(self, job: Job, fn: Any, *args: Any, **kwargs: Any) -> None:
        self._executor.submit(self._run, job, fn, *args, **kwargs)

    def _run(self, job: Job, fn: Any, *args: Any, **kwargs: Any) -> None:
        job.status = "running"
        job._event_queue.put({"event": "status", "data": {"status": "running"}})
        try:
            result = fn(*args, **kwargs)
            job.result = result
            job.status = "completed"
            job._event_queue.put(
                {"event": "completed", "data": {"job_id": job.id, "status": "completed"}}
            )
        except Exception as exc:
            logger.exception("Job %s failed", job.id)
            job.error = str(exc)
            job.status = "failed"
            job._event_queue.put(
                {
                    "event": "failed",
                    "data": {"job_id": job.id, "status": "failed", "error": str(exc)},
                }
            )

    def push_progress(self, job: Job, progress: SearchProgress) -> None:
        job.progress = progress
        job._event_queue.put(
            {
                "event": "progress",
                "data": {
                    "connection": progress.connection,
                    "current": progress.current,
                    "total": progress.total,
                    "message": progress.message,
                },
            }
        )

    async def subscribe_events(self, job_id: str) -> AsyncIterator[dict[str, Any]]:
        job = self.get_job(job_id)
        if job is None:
            return

        loop = asyncio.get_event_loop()
        while True:
            try:
                event = await loop.run_in_executor(None, job._event_queue.get, True, 1.0)
                yield event
                if event["event"] in ("completed", "failed"):
                    break
            except Empty:
                if job.status in ("completed", "failed"):
                    break
                continue
