"""The resolver and the journal linker: each runs its workflow for one agent run, with that
run's dependencies, and returns what the service stores."""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.agent.ladder import Proposal
from app.application.agent.log import RunLog
from app.application.agent.resolve_state import LinkDeps, ResolveDeps
from app.application.agent.workflows.link_journal import build_link_graph
from app.application.agent.workflows.resolve_favourite import build_resolve_graph
from app.application.ports import (
    AgentRunRepository,
    JournalRepository,
    LanguageModel,
    TasteGraph,
)
from app.domain.feedback import Blocklist
from app.domain.journal import JournalNode
from app.domain.models import FavouriteKind


@dataclass(frozen=True)
class ResolveOutcome:
    """Up to 3 proposals, or a question for the user and what "keep it as text" would save."""

    proposals: list[Proposal]
    question: str | None = None
    text_favourite: dict[str, str | None] | None = None


class AgentResolver:
    """Runs resolve_favourite. The main model interprets (it sees only what was typed)."""

    def __init__(
        self,
        taste: TasteGraph,
        runs: AgentRunRepository,
        max_searches: int,
        language_model: LanguageModel | None = None,
    ) -> None:
        self._taste = taste
        self._runs = runs
        self._max_searches = max_searches
        self._language_model = language_model

    async def resolve(
        self,
        run_id: UUID,
        profile_id: UUID,
        blocklist: Blocklist,
        text: str,
        kind: FavouriteKind | None,
        hint: str | None,
    ) -> ResolveOutcome:
        """Climb the ladder for what the user typed. The text lives only in this call."""
        deps = ResolveDeps(
            taste=self._taste,
            log=RunLog(self._runs, run_id),
            profile_id=profile_id,
            blocklist=blocklist,
            max_searches=self._max_searches,
            language_model=self._language_model,
        )
        final = await build_resolve_graph(deps).ainvoke({"text": text, "kind": kind, "hint": hint})
        return ResolveOutcome(
            proposals=final.get("proposals", []),
            question=final.get("question"),
            text_favourite=final.get("text_favourite"),
        )


@dataclass(frozen=True)
class LinkOutcome:
    """How many suggestions were saved, and whether the AI read the entry (or the rule-based
    fallback ran)."""

    suggested: int
    ai_read: bool


class AgentJournalLinker:
    """Runs link_journal. `language_model` must be the Groq-only model (rule 11)."""

    def __init__(
        self,
        taste: TasteGraph,
        journal: JournalRepository,
        runs: AgentRunRepository,
        max_searches: int,
        language_model: LanguageModel | None = None,
    ) -> None:
        self._taste = taste
        self._journal = journal
        self._runs = runs
        self._max_searches = max_searches
        self._language_model = language_model

    async def link(
        self,
        run_id: UUID,
        entry: JournalNode,
        blocklist: Blocklist,
        known_names: Sequence[tuple[str, str]],
    ) -> LinkOutcome:
        """Suggest links for one entry. Its text lives only in this call."""
        deps = LinkDeps(
            taste=self._taste,
            journal=self._journal,
            log=RunLog(self._runs, run_id),
            profile_id=entry.profile_id,
            blocklist=blocklist,
            max_searches=self._max_searches,
            language_model=self._language_model,
            known_names=tuple(known_names),
        )
        final = await build_link_graph(deps).ainvoke({"entry": entry})
        return LinkOutcome(suggested=final.get("suggested", 0), ai_read=final.get("ai_read", False))
