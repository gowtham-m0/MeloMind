"""The `FeedRow` strategy: one kind of row on the home feed.

A row says whether it applies to a profile and which rows it makes (`specs`): each spec names
the fixed Qloo queries that top it up and which research results it may take. `build_rows`
does the rest, the same way for every row, so adding a row never changes the workflow or the API.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.application.agent.types import Candidate, FeedContext, SignalRef
from app.domain.feed import RowPlacement
from app.domain.models import EntityType

RowOrder = Literal["rank", "featured", "popularity"]


@dataclass(frozen=True)
class RowQuery:
    """One fixed insights query a row may run. Exclusions are always added by the tool."""

    entity_type: EntityType
    signal_ids: tuple[str, ...] = ()
    country_code: str | None = None
    popularity_min: float | None = None
    year_min: int | None = None
    year_max: int | None = None
    take: int = 12


@dataclass(frozen=True)
class RowSpec:
    """One row to build.

    - `pool_types`: which research results the row may take.
    - `order`: by rank; by rank with the agent's featured picks first; or by popularity.
    - `mixed`: interleave types, so the row moves between music, films, TV and books.
    - `one_per_type`: at most one item of each type (cross-culture picks).
    - `reason`: a fixed reason for every card ("Popular in India right now."); otherwise each
      card's reason comes from the signal behind it.
    - `min_items`: below this the row is dropped.
    """

    key: str
    title: str
    subtitle: str = ""
    placement: RowPlacement = "main"
    queries: tuple[RowQuery, ...] = ()
    pool_types: frozenset[EntityType] = frozenset()
    mixed: bool = False
    one_per_type: bool = False
    order: RowOrder = "rank"
    reason: str | None = None
    size: int | None = None
    min_items: int = 4


class FeedRow(Protocol):
    """One kind of row. Registered in the `RowRegistry` with an order."""

    name: str

    def applies(self, context: FeedContext) -> bool:
        """Whether the profile gets this row at all."""
        ...

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """The rows to build, given the research pool."""
        ...


def entity_signals(context: FeedContext) -> list[SignalRef]:
    """Signals that are items (not tags), newest taste first."""
    return [signal for signal in context.signals if not signal.is_tag]


def cross_type_signals(context: FeedContext) -> list[SignalRef]:
    """Item signals that can steer other types. Qloo accepts a book only as a signal for books."""
    return [
        signal for signal in entity_signals(context) if signal.entity_type is not EntityType.BOOK
    ]


def top_signal_ids(context: FeedContext, count: int = 3) -> tuple[str, ...]:
    """The IDs of the strongest few signals, for a row's top-up query."""
    return tuple(signal.ref for signal in context.signals[:count])


def count_of(pool: Sequence[Candidate], entity_type: EntityType) -> int:
    """How many research results are of this type."""
    return sum(1 for candidate in pool if candidate.entity_type is entity_type)
