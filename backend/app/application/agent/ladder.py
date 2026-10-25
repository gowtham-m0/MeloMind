"""The hint ladder (docs/AGENT.md, section 4), shared by `resolve_favourite` and `link_journal`.

Code climbs it, rung by rung, and stops at the first rung with an accepted match. Every search
goes through the `search_entities` and `find_tags` tools, so it's logged and counted against the
run's search budget. A song title or a lyric never reaches Qloo: Qloo has no songs, so a song
is found through its singer, composer or film.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.agent.log import RunLog
from app.application.agent.tools.context import TYPE_NOUNS, ToolContext, ToolRefusalError
from app.application.agent.tools.find_tags import find_tags
from app.application.agent.tools.get_insights import InsightsRequest, get_insights
from app.application.agent.tools.search_entities import search_entities
from app.application.agent.types import Candidate, FeedContext
from app.application.ports import TasteGraph
from app.domain.feedback import Blocklist
from app.domain.models import EntityType, FavouriteKind
from app.domain.names import name_fits, spelling_variants

PROPOSALS_MAX = 3
YEAR_TOLERANCE = 5
SPELLING_TRIES = 2
TAG_PICKS = 3
YEAR_CHECKED_TYPES = frozenset({EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK})


@dataclass(frozen=True)
class Hints:
    """What is known about the thing the user means. `kind` is what they're after; the other
    fields are names to search (never a lyric), and `song_title` is kept but never searched."""

    kind: FavouriteKind | None = None
    title: str | None = None
    song_title: str | None = None
    singer: str | None = None
    composer: str | None = None
    film: str | None = None
    actor: str | None = None
    year: int | None = None
    tag: str | None = None


@dataclass(frozen=True)
class Proposal:
    """A match for the user to confirm. A song is proposed as its singer, with the song title
    kept alongside (only the title and singer, never a lyric)."""

    entity_id: str
    name: str
    type: EntityType
    kind: FavouriteKind
    rung: str
    why: str
    year: int | None = None
    image_url: str | None = None
    song_title: str | None = None

    def to_result(self) -> dict[str, object]:
        """The proposal as it goes into the run's result."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "type": self.type.value,
            "kind": self.kind.value,
            "year": self.year,
            "image_url": self.image_url,
            "song_title": self.song_title,
            "rung": self.rung,
            "why": self.why,
        }


def ladder_context(
    taste: TasteGraph,
    log: RunLog,
    profile_id: UUID,
    blocklist: Blocklist,
    max_searches: int,
    node: str,
    song_titles: Sequence[str] = (),
) -> ToolContext:
    """A tool context for the ladder: the profile's exclusions, the search budget, and the song
    titles `search_entities` must refuse."""
    context = FeedContext(
        profile_id=profile_id,
        first_name="",
        birth_year=None,
        country_code=None,
        favourite_signals=(),
        learned_signals=(),
        text_favourites=(),
        song_titles=tuple(title for title in song_titles if title),
        blocklist=blocklist,
    )
    return ToolContext(
        taste=taste, log=log, context=context, max_qloo_calls=max_searches, node=node
    )


class _OutOfSearchesError(Exception):
    """The run's search budget is spent: stop climbing."""


def accepts(
    candidate: Candidate, expected: EntityType | None, wanted: str, year: int | None
) -> bool:
    """The acceptance check in code: the type the rung expects, the name the user meant, and,
    for films, shows and books with both years known, a year within 5."""
    if expected is not None and candidate.entity_type is not expected:
        return False
    if not name_fits(candidate.name, wanted):
        return False
    return not (
        year is not None
        and candidate.release_year is not None
        and candidate.entity_type in YEAR_CHECKED_TYPES
        and abs(candidate.release_year - year) > YEAR_TOLERANCE
    )


async def climb(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    """Up to 3 proposals from the first rung that finds an accepted match, or none."""
    rungs = (
        _title_rung,
        _singer_rung,
        _spelling_rung,
        _composer_rung,
        _film_rung,
        _actor_rung,
        _tag_rung,
    )
    try:
        for rung in rungs:
            proposals = await rung(ctx, hints)
            if proposals:
                return proposals[:PROPOSALS_MAX]
    except _OutOfSearchesError:
        await ctx.log.warn(ctx.node, f"Used all {ctx.max_qloo_calls} searches; stopped looking.")
    return []


async def _search(
    ctx: ToolContext, name: str, expected: EntityType | None, year: int | None
) -> list[Candidate]:
    try:
        found = await search_entities(ctx, name, expected)
    except ToolRefusalError:
        if ctx.budget_used:
            raise _OutOfSearchesError from None
        return []
    accepted = [c for c in found if accepts(c, expected, name, year)]
    if found and not accepted:
        await ctx.log.info(ctx.node, f"None of them is {name}, so kept looking ✗.")
    return accepted


def _target_type(kind: FavouriteKind | None) -> EntityType | None:
    if kind is None:
        return None
    return EntityType.ARTIST if kind is FavouriteKind.SONG else EntityType(kind.value)


def _proposals(found: Sequence[Candidate], hints: Hints, rung: str, why: str) -> list[Proposal]:
    proposals: list[Proposal] = []
    for candidate in found:
        is_song = hints.song_title is not None and candidate.entity_type is EntityType.ARTIST
        proposals.append(
            Proposal(
                entity_id=candidate.entity_id,
                name=candidate.name,
                type=candidate.entity_type,
                kind=FavouriteKind.SONG if is_song else FavouriteKind(candidate.entity_type.value),
                rung=rung,
                why=why,
                year=candidate.release_year,
                image_url=candidate.image_url,
                song_title=hints.song_title if is_song else None,
            )
        )
    return proposals


async def _title_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    if not hints.title or hints.kind is FavouriteKind.SONG:
        return []
    found = await _search(ctx, hints.title, _target_type(hints.kind), hints.year)
    noun = TYPE_NOUNS[found[0].entity_type] if found else "match"
    return _proposals(found, hints, "title", f"The {noun} you named.")


async def _singer_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    if not hints.singer:
        return []
    found = await _search(ctx, hints.singer, EntityType.ARTIST, None)
    why = "Sings the song you described." if hints.song_title else "The artist you named."
    return _proposals(found, hints, "singer", why)


async def _spelling_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    name = hints.singer or (hints.title if hints.kind is not FavouriteKind.SONG else None)
    if not name:
        return []
    expected = EntityType.ARTIST if hints.singer else _target_type(hints.kind)
    for variant in spelling_variants(name)[:SPELLING_TRIES]:
        found = await _search(ctx, variant, expected, hints.year)
        if found:
            return _proposals(found, hints, "spelling", f"Found under the spelling {variant}.")
    return []


async def _composer_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    if not hints.composer:
        return []
    found = await _search(ctx, hints.composer, EntityType.ARTIST, None)
    plain = Hints(kind=FavouriteKind.ARTIST)
    return _proposals(found, plain, "composer", "Composed the music you described.")


async def _film_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    if not hints.film:
        return []
    found = await _search(ctx, hints.film, EntityType.MOVIE, hints.year)
    plain = Hints(kind=FavouriteKind.MOVIE)
    why = "The film the song comes from." if hints.song_title else "The film you described."
    return _proposals(found, plain, "film", why)


async def _actor_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    if not hints.actor:
        return []
    found = await _search(ctx, hints.actor, EntityType.ARTIST, None)
    return _proposals(found, Hints(kind=FavouriteKind.ARTIST), "actor", "The star you described.")


async def _tag_rung(ctx: ToolContext, hints: Hints) -> list[Proposal]:
    """A genre or region: the tag's most popular artists, as a last suggestion."""
    if not hints.tag:
        return []
    try:
        tags = await find_tags(ctx, hints.tag)
    except ToolRefusalError:
        if ctx.budget_used:
            raise _OutOfSearchesError from None
        return []
    if not tags:
        return []
    tag = tags[0]
    try:
        found = await get_insights(
            ctx, InsightsRequest(EntityType.ARTIST, signal_ids=(tag.tag_id,), take=TAG_PICKS)
        )
    except ToolRefusalError:
        if ctx.budget_used:
            raise _OutOfSearchesError from None
        return []
    plain = Hints(kind=FavouriteKind.ARTIST)
    return _proposals(found, plain, "tag", f"Popular in {tag.name}, which you described.")
