"""Running work after a request has returned, such as an agent run the frontend then polls."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Protocol

logger = logging.getLogger(__name__)

Job = Callable[[], Awaitable[None]]


class BackgroundRunner(Protocol):
    """Starts a job without waiting for it. Tests use one that runs the job straight away."""

    async def spawn(self, job: Job) -> None:
        """Start the job. Its errors are the job's own to handle."""
        ...


class AsyncioBackgroundRunner:
    """Runs jobs as asyncio tasks, keeping a reference so they aren't garbage-collected."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[None]] = set()

    async def spawn(self, job: Job) -> None:
        """Start the job as a task."""
        task = asyncio.create_task(self._guard(job))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def close(self) -> None:
        """Cancel unfinished jobs, on shutdown."""
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    @staticmethod
    async def _guard(job: Job) -> None:
        try:
            await job()
        except Exception:
            logger.exception("A background job failed")
