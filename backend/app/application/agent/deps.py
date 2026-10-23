"""What the plan_session nodes depend on: ports, the run's log, the mode and the limits.

The workflow builder injects these, so nodes never import an adapter.
"""

from dataclasses import dataclass

from app.application.agent.log import RunLog
from app.application.modes.base import SessionMode
from app.application.ports import (
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    LanguageModel,
    MediaResolver,
    TasteGraph,
)


@dataclass(frozen=True)
class AgentLimits:
    """The agent's bounds (CLAUDE.md, "Limits"), from the settings."""

    max_tool_calls: int = 12
    max_model_calls: int = 8
    timeout_seconds: float = 25.0
    max_retries: int = 2


@dataclass(frozen=True)
class PlanDeps:
    """Everything one plan run's nodes need."""

    feedback: FeedbackRepository
    exclusions: ExclusionRepository
    taste: TasteGraph
    media: MediaResolver
    log: RunLog
    mode: SessionMode
    limits: AgentLimits
    target_minutes: int
    language_model: LanguageModel | None = None
    chat_models: ChatModels | None = None
