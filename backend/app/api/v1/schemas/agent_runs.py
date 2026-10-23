"""Response schema for agent runs: the plain-English log the frontend polls."""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel

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
    """A run and its log. `result` is a small summary once the run is done or failed."""

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
            result=run.result,
        )
