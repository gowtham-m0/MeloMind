"""The feed's rows (CLAUDE.md, "The feed"). Each is a small strategy; `build_rows` builds them."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from app.application.agent.types import ALL_TYPES, Candidate, FeedContext
from app.application.rows.base import (
    RowQuery,
    RowSpec,
    count_of,
    cross_type_signals,
    entity_signals,
    top_signal_ids,
)
from app.domain.countries import country_name
from app.domain.models import EntityType

# Top-up and fixed queries ask for a little more than a row shows, to survive dedupe.
TOPUP_TAKE = 16
BECAUSE_ROWS = 2
CROSS_TAKE = 6
POPULAR_FLOOR = 0.8
COLD_POPULAR_FLOOR = 0.7
THROWBACK_FLOOR = 0.6
RECENT_YEARS = 1
RECENT_POPULAR_FLOOR = 0.7


@dataclass(frozen=True)
class ForYouRow:
    """The research agent's best mixed picks."""

    name: str = "for_you"
    row_size: int = 12

    def applies(self, context: FeedContext) -> bool:
        """Always."""
        return True

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """One mixed row from the pool."""
        return [
            RowSpec(
                key="for_you",
                title="Recommended for you",
                subtitle="Based on your taste across music, films, TV and books",
                pool_types=frozenset(ALL_TYPES),
                mixed=True,
                order="featured",
            )
        ]


_VERBS = {
    EntityType.ARTIST: "Listen",
    EntityType.MOVIE: "Watch",
    EntityType.TV_SHOW: "Watch",
    EntityType.BOOK: "Read",
}


def verb_for(entity_type: EntityType) -> str:
    """Listen, Watch or Read: how the cross-culture rail labels each pick."""
    return _VERBS[entity_type]


@dataclass(frozen=True)
class CrossCultureRow:
    """The right rail: one pick of each other type for the newest signal that can cross types
    (an artist, film or show: Qloo uses a book only for books)."""

    name: str = "cross_culture"

    def applies(self, context: FeedContext) -> bool:
        """When there's an artist, film or show signal."""
        return bool(cross_type_signals(context))

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """One query per other type with the signal; one of its own type from the pool."""
        signal = cross_type_signals(context)[0]
        own = signal.entity_type or EntityType.ARTIST
        others = [entity_type for entity_type in ALL_TYPES if entity_type is not own]
        return [
            RowSpec(
                key="cross_culture",
                title="Cross-culture picks",
                subtitle=f"Because you like {signal.name}…",
                placement="rail",
                queries=tuple(
                    RowQuery(entity_type=other, signal_ids=(signal.ref,), take=CROSS_TAKE)
                    for other in others
                ),
                pool_types=frozenset({own}),
                one_per_type=True,
                size=len(ALL_TYPES),
                min_items=2,
                reason=f"Because you like {signal.name}.",
            )
        ]


@dataclass(frozen=True)
class BecauseRow:
    """ "Because you liked X": more of the same type, for the newest strong signals."""

    name: str = "because"

    def applies(self, context: FeedContext) -> bool:
        """When there's at least one item signal."""
        return bool(entity_signals(context))

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """Up to two rows, one per signal."""
        return [
            RowSpec(
                key=f"because_{signal.ref}",
                title=f"Because you liked {signal.name}",
                subtitle="More like it, picked by Qloo",
                queries=(
                    RowQuery(
                        entity_type=signal.entity_type or EntityType.ARTIST,
                        signal_ids=(signal.ref,),
                        take=TOPUP_TAKE,
                    ),
                ),
                reason=f"Because you liked {signal.name}.",
            )
            for signal in entity_signals(context)[:BECAUSE_ROWS]
        ]


@dataclass(frozen=True)
class TypeRow:
    """One type: research results of that type, topped up when there are too few."""

    name: str
    entity_type: EntityType
    title: str
    subtitle: str
    row_size: int = 12

    def applies(self, context: FeedContext) -> bool:
        """Always."""
        return True

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """A top-up query only when the pool is short of this type."""
        queries: tuple[RowQuery, ...] = ()
        if count_of(pool, self.entity_type) < self.row_size:
            signals = top_signal_ids(context)
            if signals:
                queries = (
                    RowQuery(entity_type=self.entity_type, signal_ids=signals, take=TOPUP_TAKE),
                )
            elif self.entity_type is not EntityType.ARTIST:
                # Nothing known yet: popular picks. Artists need a signal (QLOO_NOTES, §3).
                queries = (
                    RowQuery(
                        entity_type=self.entity_type,
                        country_code=context.country_code,
                        popularity_min=COLD_POPULAR_FLOOR,
                        take=TOPUP_TAKE,
                    ),
                )
        return [
            RowSpec(
                key=self.name,
                title=self.title,
                subtitle=self.subtitle,
                queries=queries,
                pool_types=frozenset({self.entity_type}),
            )
        ]


@dataclass(frozen=True)
class PopularRow:
    """Films and TV popular in the user's country, steered by their taste."""

    name: str = "popular"

    def applies(self, context: FeedContext) -> bool:
        """When the country is set and Qloo knows its name."""
        return bool(context.country_code and country_name(context.country_code))

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """Films and TV with the country filter and a high popularity floor."""
        code = context.country_code or ""
        place = country_name(code) or code
        signals = top_signal_ids(context)
        return [
            RowSpec(
                key=f"popular_{code.lower()}",
                title=f"Popular in {place}",
                subtitle="What people around you are watching, matched to your taste",
                queries=tuple(
                    RowQuery(
                        entity_type=entity_type,
                        signal_ids=signals,
                        country_code=code,
                        popularity_min=POPULAR_FLOOR,
                        take=TOPUP_TAKE,
                    )
                    for entity_type in (EntityType.MOVIE, EntityType.TV_SHOW)
                ),
                mixed=True,
                order="popularity",
                reason=f"Popular in {place} right now.",
            )
        ]


@dataclass(frozen=True)
class NewReleasesRow:
    """Films and TV from the last couple of years, steered by taste."""

    name: str = "new"

    def applies(self, context: FeedContext) -> bool:
        """Always."""
        return True

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """Recent films and TV; popular ones when there's no taste to follow yet."""
        since = date.today().year - RECENT_YEARS
        signals = top_signal_ids(context)
        return [
            RowSpec(
                key="new",
                title="New and notable",
                subtitle=f"Films and shows from {since} on, matched to your taste",
                queries=tuple(
                    RowQuery(
                        entity_type=entity_type,
                        signal_ids=signals,
                        popularity_min=None if signals else RECENT_POPULAR_FLOOR,
                        country_code=None if signals else context.country_code,
                        year_min=since,
                        take=TOPUP_TAKE,
                    )
                    for entity_type in (EntityType.MOVIE, EntityType.TV_SHOW)
                ),
                mixed=True,
                reason="Recent and close to your taste." if signals else "A recent hit.",
            )
        ]


@dataclass(frozen=True)
class ThrowbackRow:
    """Films and TV from the user's teens, when the birth year is known."""

    name: str = "throwback"

    def applies(self, context: FeedContext) -> bool:
        """When the birth year is set."""
        return context.era is not None

    def specs(self, context: FeedContext, pool: Sequence[Candidate]) -> list[RowSpec]:
        """Films and TV in the era window, popular ones, steered by taste."""
        start, end = context.era or (0, 0)
        signals = top_signal_ids(context)
        return [
            RowSpec(
                key="throwback",
                title="Throwback: your teens",
                subtitle=f"Big films and shows from {start}–{end}",
                queries=tuple(
                    RowQuery(
                        entity_type=entity_type,
                        signal_ids=signals,
                        popularity_min=THROWBACK_FLOOR,
                        year_min=start,
                        year_max=end,
                        take=TOPUP_TAKE,
                    )
                    for entity_type in (EntityType.MOVIE, EntityType.TV_SHOW)
                ),
                mixed=True,
                order="popularity",
                reason="A favourite from your teens.",
            )
        ]
