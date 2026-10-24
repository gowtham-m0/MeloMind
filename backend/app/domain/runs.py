"""Agent runs and their plain-English log, shown to the user as the agent works."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.domain.models import utc_now


class RunKind(StrEnum):
    """Which workflow the run belongs to."""

    FEED = "feed"
    RESOLVE = "resolve"
    LINK = "link"


class RunStatus(StrEnum):
    """Whether the run is still going."""

    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StepLevel(StrEnum):
    """How a log step should look: a normal step, or something that went wrong."""

    INFO = "info"
    WARNING = "warning"


@dataclass(frozen=True)
class AgentStep:
    """One log entry: which node wrote it and what happened, in plain English."""

    node: str
    message: str
    level: StepLevel = StepLevel.INFO
    at: datetime = field(default_factory=utc_now)


@dataclass
class AgentRun:
    """One run of a workflow. `result` holds a small summary once it's done."""

    profile_id: UUID
    kind: RunKind
    status: RunStatus = RunStatus.RUNNING
    steps: list[AgentStep] = field(default_factory=list)
    result: dict[str, Any] | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
