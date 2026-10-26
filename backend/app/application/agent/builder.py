"""The feed builder: runs the build_feed workflow for one profile and returns the finished feed."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.application.agent.deps import AgentLimits, FeedDeps
from app.application.agent.log import RunLog
from app.application.agent.taste_match import MatchResult, match_tastes
from app.application.agent.types import AskIntent
from app.application.agent.workflows.ask import build_ask_graph
from app.application.agent.workflows.build_feed import build_feed_graph
from app.application.ports import (
    AgentRunRepository,
    ChatModels,
    ExclusionRepository,
    FeedbackRepository,
    JournalRepository,
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
class AskRequest:
    """One extra row to build: whose, the run that logs it, what they asked and what the feed
    already shows."""

    profile: Profile
    run_id: UUID
    intent: AskIntent
    previous_refs: frozenset[str] = frozenset()


@dataclass(frozen=True)
class MatchRequest:
    """A taste match: `profile` with another profile of the owner, or with a friend's favourites
    (Qloo entity IDs)."""

    profile: Profile
    run_id: UUID
    other: Profile | None = None
    friend_ids: tuple[str, ...] = ()


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
        journal: JournalRepository | None = None,
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
        self._journal = journal

    def _deps(
        self,
        run_id: UUID,
        previous_refs: frozenset[str] = frozenset(),
        previous_tags: tuple[str, ...] = (),
    ) -> FeedDeps:
        return FeedDeps(
            feedback=self._feedback,
            exclusions=self._exclusions,
            taste=self._taste,
            log=RunLog(self._runs, run_id),
            rows=self._rows,
            limits=self._limits,
            language_model=self._language_model,
            chat_models=self._chat_models,
            songs=self._songs,
            previous_refs=previous_refs,
            previous_tags=previous_tags,
            journal=self._journal,
        )

    async def ask(self, request: AskRequest) -> FeedRow | None:
        """Run the ask workflow: one extra row, or None when nothing new was found."""
        deps = self._deps(request.run_id, request.previous_refs)
        final = await build_ask_graph(deps, request.intent).ainvoke({"profile": request.profile})
        rows: list[FeedRow] = final.get("rows", [])
        return rows[0] if rows else None

    async def match(self, request: MatchRequest) -> MatchResult:
        """Compare two tastes and build the "For you both" row."""
        deps = self._deps(request.run_id)
        return await match_tastes(deps, request.profile, request.other, request.friend_ids)

    async def build(self, request: FeedRequest) -> FeedResult:
        """Run build_feed to the end. A feed is always produced unless a port breaks."""
        deps = self._deps(request.run_id, request.previous_refs, request.previous_tags)
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
