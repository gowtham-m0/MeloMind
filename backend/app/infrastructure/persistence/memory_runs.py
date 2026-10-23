"""`AgentRunRepository` in memory."""

from copy import deepcopy
from typing import Any
from uuid import UUID

from app.domain.models import utc_now
from app.domain.runs import AgentRun, AgentStep, RunStatus


class InMemoryAgentRunRepository:
    """Runs by ID. Steps are appended in place, as the agent works."""

    def __init__(self) -> None:
        self._runs: dict[UUID, AgentRun] = {}

    async def add(self, run: AgentRun) -> None:
        """Store a new run."""
        self._runs[run.id] = deepcopy(run)

    async def get(self, run_id: UUID) -> AgentRun | None:
        """One run with its log."""
        run = self._runs.get(run_id)
        return deepcopy(run) if run else None

    async def append_step(self, run_id: UUID, step: AgentStep) -> None:
        """Add one entry to the run's log."""
        run = self._runs.get(run_id)
        if run is not None:
            run.steps.append(step)

    async def finish(self, run_id: UUID, status: RunStatus, result: dict[str, Any] | None) -> None:
        """Mark the run done or failed."""
        run = self._runs.get(run_id)
        if run is not None:
            run.status = status
            run.result = deepcopy(result)
            run.finished_at = utc_now()
