"""`AgentRunRepository` on Postgres. The log is a JSONB array, appended to atomically."""

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import cast, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import utc_now
from app.domain.runs import AgentRun, AgentStep, RunKind, RunStatus, StepLevel
from app.infrastructure.persistence.models import AgentRunRow


def _step_to_json(step: AgentStep) -> dict[str, Any]:
    return {
        "node": step.node,
        "message": step.message,
        "level": step.level.value,
        "at": step.at.isoformat(),
    }


def _step_to_domain(raw: dict[str, Any]) -> AgentStep:
    return AgentStep(
        node=raw["node"],
        message=raw["message"],
        level=StepLevel(raw.get("level", StepLevel.INFO.value)),
        at=datetime.fromisoformat(raw["at"]),
    )


def _run_to_domain(row: AgentRunRow) -> AgentRun:
    return AgentRun(
        id=row.id,
        profile_id=row.profile_id,
        kind=RunKind(row.kind),
        status=RunStatus(row.status),
        steps=[_step_to_domain(step) for step in row.steps],
        result=row.result,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


class PostgresAgentRunRepository:
    """Agent runs in Postgres."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, run: AgentRun) -> None:
        """Store a new run."""
        async with self._sessions() as db, db.begin():
            db.add(
                AgentRunRow(
                    id=run.id,
                    profile_id=run.profile_id,
                    kind=run.kind.value,
                    status=run.status.value,
                    steps=[_step_to_json(step) for step in run.steps],
                    result=run.result,
                    created_at=run.created_at,
                    finished_at=run.finished_at,
                )
            )

    async def get(self, run_id: UUID) -> AgentRun | None:
        """One run with its log."""
        async with self._sessions() as db:
            row = await db.get(AgentRunRow, run_id)
            return _run_to_domain(row) if row else None

    async def append_step(self, run_id: UUID, step: AgentStep) -> None:
        """Add one entry to the log in a single statement, so parallel steps never clash."""
        entry = cast(json.dumps([_step_to_json(step)]), JSONB)
        async with self._sessions() as db, db.begin():
            await db.execute(
                update(AgentRunRow)
                .where(AgentRunRow.id == run_id)
                .values(steps=AgentRunRow.steps.op("||")(entry))
            )

    async def finish(self, run_id: UUID, status: RunStatus, result: dict[str, Any] | None) -> None:
        """Mark the run done or failed."""
        async with self._sessions() as db, db.begin():
            await db.execute(
                update(AgentRunRow)
                .where(AgentRunRow.id == run_id)
                .values(status=status.value, result=result, finished_at=utc_now())
            )
