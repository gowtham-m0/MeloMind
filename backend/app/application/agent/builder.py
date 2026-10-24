"""The feed builder: runs the build_feed workflow for one profile and returns the finished feed."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.application.agent.deps import AgentLimits, FeedDeps
from app.application.agent.log import RunLog
from app.application.agent.workflows.build_feed import build_feed_graph
from app.application.ports import (
    AgentRunRepository,
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    LanguageModel,
    SongCatalog,
    TasteGraph,
)
from app.application.rows.registry import RowRegistry
from app.domain.feed import FeedItem, FeedRow
from app.domain.models import Profile


@dataclass(frozen=True)
class FeedRequest:
    """One feed to build: whose, the run that logs it, and what the last feed showed."""

    profile: Profile
    run_id: UUID
    previous_refs: frozenset[str] = frozenset()
    previous_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeedResult:
    """The built feed, and a small summary for the run's result."""

    hero: FeedItem | None
    rows: list[FeedRow]
    summary: str
    taste_tags: tuple[str, ...]
    run_summary: dict[str, Any] = field(default_factory=dict)


class AgentFeedBuilder:
    """Builds the workflow with this run's dependencies and runs it."""

    def __init__(
        self,
        *,
        feedback: FeedbackRepository,
        exclusions: ExclusionRepository,
        taste: TasteGraph,
        runs: AgentRunRepository,
        rows: RowRegistry,
        limits: AgentLimits,
        language_model: LanguageModel | None = None,
        chat_models: ChatModels | None = None,
        songs: SongCatalog | None = None,
    ) -> None:
        self._feedback = feedback
        self._exclusions = exclusions
        self._taste = taste
        self._runs = runs
        self._rows = rows
        self._limits = limits
        self._language_model = language_model
        self._chat_models = chat_models
        self._songs = songs

    async def build(self, request: FeedRequest) -> FeedResult:
        """Run build_feed to the end. A feed is always produced unless a port breaks."""
        deps = FeedDeps(
            feedback=self._feedback,
            exclusions=self._exclusions,
            taste=self._taste,
            log=RunLog(self._runs, request.run_id),
            rows=self._rows,
            limits=self._limits,
            language_model=self._language_model,
            chat_models=self._chat_models,
            songs=self._songs,
            previous_refs=request.previous_refs,
            previous_tags=request.previous_tags,
        )
        final = await build_feed_graph(deps).ainvoke({"profile": request.profile})
        rows: list[FeedRow] = final.get("rows", [])
        hero: FeedItem | None = final.get("hero_item")
        return FeedResult(
            hero=hero,
            rows=rows,
            summary=final.get("summary", ""),
            taste_tags=final.get("taste_tags", ()),
            run_summary={
                "research_outcome": final.get("research_outcome"),
                "fallback_attempts": final.get("fallback_attempts", 0),
                "row_count": len(rows),
                "item_count": sum(len(row.items) for row in rows) + (1 if hero else 0),
                "source": self._taste.source,
            },
        )
