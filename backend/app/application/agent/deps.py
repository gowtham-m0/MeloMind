"""What the build_feed nodes depend on: ports, the run's log, the rows and the limits.

The workflow builder injects these, so nodes never import an adapter.
"""

from dataclasses import dataclass

from app.application.agent.log import RunLog
from app.application.ports import (
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    LanguageModel,
    TasteGraph,
)
from app.application.rows.registry import RowRegistry


@dataclass(frozen=True)
class AgentLimits:
    """The agent's bounds (CLAUDE.md, "Limits"), from the settings."""

    max_tool_calls: int = 12
    max_model_calls: int = 8
    timeout_seconds: float = 25.0
    max_retries: int = 2
    feed_max_qloo_calls: int = 24
    row_size: int = 12


@dataclass(frozen=True)
class FeedDeps:
    """Everything one feed run's nodes need. `previous_refs` and `previous_tags` describe the
    last feed, so the summary can say what changed."""

    feedback: FeedbackRepository
    exclusions: ExclusionRepository
    taste: TasteGraph
    log: RunLog
    rows: RowRegistry
    limits: AgentLimits
    language_model: LanguageModel | None = None
    chat_models: ChatModels | None = None
    previous_refs: frozenset[str] = frozenset()
    previous_tags: tuple[str, ...] = ()
