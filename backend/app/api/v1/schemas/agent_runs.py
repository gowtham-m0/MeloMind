"""Response schema for agent runs: the plain-English log the frontend polls."""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel

from app.api.v1.schemas.feed import FeedRowOut
from app.domain.feed_json import row_from_json
from app.domain.runs import AgentRun, AgentStep, RunKind, RunStatus, StepLevel


class AgentStepOut(BaseModel):
    """One log entry."""

    node: str
    message: str
    level: StepLevel
    at: datetime

    @classmethod
    def from_domain(cls, step: AgentStep) -> Self:
        """Build from the domain value."""
        return cls(node=step.node, message=step.message, level=step.level, at=step.at)


class AgentRunOut(BaseModel):
    """A run and its log. `result` is a small summary once the run is done or failed. For a
    finished ask run it is the row, shaped like a feed row."""

    id: UUID
    kind: RunKind
    status: RunStatus
    steps: list[AgentStepOut]
    result: dict[str, Any] | None

    @classmethod
    def from_domain(cls, run: AgentRun) -> Self:
        """Build from the domain entity."""
        return cls(
            id=run.id,
            kind=run.kind,
            status=run.status,
            steps=[AgentStepOut.from_domain(step) for step in run.steps],
            result=_result(run),
        )


def _result(run: AgentRun) -> dict[str, Any] | None:
    """The run's result. An ask run stores its row as domain JSON; clients get a feed row."""
    if run.kind is RunKind.ASK and run.status is RunStatus.DONE and run.result:
        return FeedRowOut.from_domain(row_from_json(run.result), {}).model_dump(mode="json")
    return run.result
