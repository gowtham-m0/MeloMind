"""`get_insights`: recommendations over `TasteGraph.insights`.

It always adds the profile's exclusions itself (rule 7), and sends only what Qloo supports for
the type: years for films, TV and books; a country for films and TV.
"""

from dataclasses import dataclass

from app.application.agent.tools.context import TYPE_PLURALS, ToolContext, ToolRefusalError
from app.application.agent.types import Candidate
from app.application.ports import InsightsQuery
from app.core.errors import UpstreamError
from app.domain.models import EntityType

TAKE_MIN = 1
TAKE_MAX = 30
YEAR_MIN = 1900
YEAR_MAX = 2030
SIGNALS_MAX = 10
YEAR_FILTER_TYPES = frozenset({EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK})
COUNTRY_FILTER_TYPES = frozenset({EntityType.MOVIE, EntityType.TV_SHOW})


@dataclass(frozen=True)
class InsightsRequest:
    """One insights call. `signal_ids` mixes entity and tag IDs; the tool sorts them out."""

    entity_type: EntityType
    signal_ids: tuple[str, ...] = ()
    year_min: int | None = None
    year_max: int | None = None
    country_code: str | None = None
    popularity_min: float | None = None
    take: int = 10


async def get_insights(ctx: ToolContext, request: InsightsRequest) -> list[Candidate]:
    """Candidates of one type for the signals, never including an excluded item.

    With no signals, films, TV and books need a popularity floor (popular picks for a cold
    start); artists always need a signal, because without one Qloo returns generic bands.
    """
    entity_type = request.entity_type
    known = [ref for ref in dict.fromkeys(request.signal_ids) if ctx.name_of(ref) is not None]
    tags = tuple(ref for ref in known if ctx.is_tag(ref))[:SIGNALS_MAX]
    entities = tuple(ref for ref in known if not ctx.is_tag(ref))
    if entity_type is not EntityType.BOOK:
        # Qloo rejects book signals for any other type (QLOO_NOTES, section 3).
        entities = tuple(ref for ref in entities if ctx.type_of(ref) is not EntityType.BOOK)
    entities = entities[:SIGNALS_MAX]
    if not tags and not entities:
        if entity_type is EntityType.ARTIST:
            raise ToolRefusalError(
                "Artists need an entity or tag signal, such as a film or a genre tag."
            )
        if request.popularity_min is None:
            raise ToolRefusalError(
                "Give at least one signal ID from the brief or your tool results, or a "
                "popularity_min for popular picks. Unknown IDs are ignored."
            )
    year_min, year_max = _years(request) if entity_type in YEAR_FILTER_TYPES else (None, None)
    country = request.country_code if entity_type in COUNTRY_FILTER_TYPES else None
    query = InsightsQuery(
        entity_type=entity_type,
        take=min(max(request.take, TAKE_MIN), TAKE_MAX),
        signal_entities=entities,
        signal_tags=tags,
        year_min=year_min,
        year_max=year_max,
        country_code=country.upper() if country and len(country) == 2 else None,
        popularity_min=_clamp(request.popularity_min),
        exclude_entities=ctx.context.blocklist.qloo_ids,
    )
    basis, because = _basis(ctx, entity_type, entities, tags, country)
    asked = f"{TYPE_PLURALS[entity_type]} {basis}" + _era_text(year_min, year_max)
    await ctx.spend_qloo_call()
    try:
        matches = await ctx.taste.insights(query)
    except UpstreamError:
        await ctx.log.warn(ctx.node, f"Asked Qloo for {asked} → Qloo didn't answer.")
        return []
    found = [
        Candidate(
            entity_id=match.entity_id,
            name=match.name,
            entity_type=match.type,
            source=ctx.source,
            signal=basis,
            because_ref=because,
            because_name=ctx.name_of(because) if because else None,
            release_year=match.release_year,
            popularity=match.popularity,
            affinity=match.affinity,
            image_url=match.image_url,
            description=match.description,
            isbn13=match.isbn13,
            tags=match.tags,
            external=tuple(sorted(match.external.items())),
        )
        for match in matches
        if not ctx.context.blocklist.blocks(match.entity_id, match.name)
    ]
    for candidate in found:
        ctx.remember(candidate)
        ctx.recommended.add(candidate.entity_id)
    await ctx.log.info(ctx.node, f"Asked Qloo for {asked} → {len(found)} found.")
    return found


def _years(request: InsightsRequest) -> tuple[int | None, int | None]:
    low = _clamp_year(request.year_min)
    high = _clamp_year(request.year_max)
    if low is not None and high is not None and low > high:
        low, high = high, low
    return low, high


def _clamp_year(year: int | None) -> int | None:
    return None if year is None else min(max(year, YEAR_MIN), YEAR_MAX)


def _clamp(value: float | None) -> float | None:
    return None if value is None else min(max(value, 0.0), 1.0)


def _era_text(year_min: int | None, year_max: int | None) -> str:
    if year_min is not None and year_max is not None:
        return f", {year_min}–{year_max}"
    if year_min is not None:
        return f", from {year_min}"
    if year_max is not None:
        return f", up to {year_max}"
    return ""


def _basis(
    ctx: ToolContext,
    entity_type: EntityType,
    entities: tuple[str, ...],
    tags: tuple[str, ...],
    country: str | None,
) -> tuple[str, str | None]:
    """The reason basis in plain English, such as "similar to The Strokes, which you love", and
    the item behind it. Signals of the same type come first: a film is "similar to" a film."""
    if entities:
        ordered = sorted(entities, key=lambda ref: ctx.type_of(ref) is not entity_type)[:2]
        names = _join([ctx.name_of(ref) or "" for ref in ordered])
        loved = any(ctx.is_loved(ref) for ref in ordered)
        basis = f"similar to {names}, which you love" if loved else f"similar to {names}"
        return basis, ordered[0]
    if tags:
        return f"linked to {_join([ctx.name_of(ref) or '' for ref in tags[:2]])}", None
    if country:
        return "popular where you are", None
    return "popular right now", None


def _join(names: list[str]) -> str:
    names = [name for name in names if name]
    return " and ".join(names) if len(names) <= 2 else ", ".join(names[:-1]) + " and " + names[-1]
