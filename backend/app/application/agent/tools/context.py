"""What the tools share during one run: the ports, the log, the budget and what has been seen."""

from dataclasses import dataclass, field

from app.application.agent.log import RunLog
from app.application.agent.types import Candidate, PlanContext
from app.application.ports import TasteGraph
from app.domain.models import EntityType
from app.domain.sessions import ItemSource

TYPE_NOUNS: dict[EntityType, str] = {
    EntityType.ARTIST: "artist",
    EntityType.MOVIE: "film",
    EntityType.TV_SHOW: "TV show",
    EntityType.BOOK: "book",
}
TYPE_PLURALS: dict[EntityType, str] = {
    EntityType.ARTIST: "artists",
    EntityType.MOVIE: "films",
    EntityType.TV_SHOW: "TV shows",
    EntityType.BOOK: "books",
}


def count_noun(count: int, entity_type: EntityType) -> str:
    """A count and its noun, such as "1 film" or "2 films"."""
    return f"{count} {TYPE_NOUNS[entity_type] if count == 1 else TYPE_PLURALS[entity_type]}"


NO_CALLS_LEFT = "No Qloo calls are left. Call submit_candidates now with what you have."


class ToolRefusalError(Exception):
    """A tool call that was refused before reaching Qloo. The message goes back to the agent."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class ToolContext:
    """One run's shared tool state. `seen` holds every entity a tool returned, and
    `recommended` the ones Qloo recommended through insights: only those can be submitted, so
    every candidate is a Qloo recommendation, never something the agent made up (rule 9)."""

    taste: TasteGraph
    log: RunLog
    context: PlanContext
    max_qloo_calls: int
    node: str = "research"
    qloo_calls: int = 0
    seen: dict[str, Candidate] = field(default_factory=dict)
    recommended: set[str] = field(default_factory=set)
    tag_names: dict[str, str] = field(default_factory=dict)
    submitted: dict[str, Candidate] = field(default_factory=dict)
    _budget_logged: bool = False

    @property
    def source(self) -> ItemSource:
        """Where this run's results come from."""
        return ItemSource(self.taste.source)

    @property
    def budget_used(self) -> bool:
        """True once every Qloo call has been spent."""
        return self.qloo_calls >= self.max_qloo_calls

    async def spend_qloo_call(self) -> None:
        """Count one Qloo call, or refuse it when the budget is used up."""
        if self.budget_used:
            if not self._budget_logged:
                self._budget_logged = True
                await self.log.warn(self.node, f"Used all {self.max_qloo_calls} Qloo calls.")
            raise ToolRefusalError(NO_CALLS_LEFT)
        self.qloo_calls += 1

    def remember(self, candidate: Candidate) -> None:
        """Keep an entity a tool returned. An insights result replaces a plain search match."""
        known = self.seen.get(candidate.entity_id)
        if known is None or (known.affinity is None and candidate.affinity is not None):
            self.seen[candidate.entity_id] = candidate

    def is_tag(self, ref: str) -> bool:
        """True when the ref is a tag found this run or given in the brief."""
        return ref in self.tag_names or any(
            signal.ref == ref and signal.is_tag for signal in self.context.signals
        )

    def name_of(self, ref: str) -> str | None:
        """The name behind an entity or tag ID this run knows, or None for an unknown ID."""
        for signal in self.context.signals:
            if signal.ref == ref:
                return signal.name
        if ref in self.seen:
            return self.seen[ref].name
        return self.tag_names.get(ref)

    def type_of(self, ref: str) -> EntityType | None:
        """The entity type behind an ID this run knows, or None for a tag or an unknown ID."""
        for signal in self.context.signals:
            if signal.ref == ref:
                return signal.entity_type
        return self.seen[ref].entity_type if ref in self.seen else None

    def is_loved(self, ref: str) -> bool:
        """True for a favourite or a learned item: something they're known to enjoy."""
        return any(signal.ref == ref for signal in self.context.signals)
