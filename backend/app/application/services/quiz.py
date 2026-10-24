"""The onboarding taste quiz ("this or that"): two big cards at a time.

The set is built from the user's own favourites: Qloo's picks for each type with their newest
favourites as signals, so every card is something their taste already points to. Without
favourites it falls back to recent, popular films and TV for their country.

The first pair is two different types. After each pick, the next pair is the unseen item most
like the pick (Qloo scores the set), plus one of another type to keep exploring. Each pick is a
`quiz_pick` signal; the card not picked gets nothing, because not choosing isn't disliking.
"""

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.application.agent.cards import candidate_from_match, to_card
from app.application.ports import EntityMatch, ExclusionRepository, InsightsQuery, TasteGraph
from app.application.services.feedback import FeedbackService, ItemRef
from app.application.services.profiles import ProfileService
from app.application.services.taste import TasteService
from app.core.errors import InvalidInputError, UpstreamError
from app.domain.feed import FeedItem, entity_type_of, favourite_ref
from app.domain.feedback import Blocklist, Signal
from app.domain.models import EntityType, Profile

logger = logging.getLogger(__name__)

POPULAR_REASON = "Popular right now."
FILM_TAKE = 8
TV_TAKE = 6
BOOK_TAKE = 4
ARTIST_TAKE = 6
SET_POPULARITY = 0.8
BOOK_POPULARITY = 0.6
ARTIST_SIGNALS = 3
SEED_SIGNALS = 2
RECENT_YEARS = 6


@dataclass(frozen=True)
class QuizEntry:
    """One candidate card and why it's in the quiz."""

    match: EntityMatch
    reason: str


@dataclass(frozen=True)
class QuizStep:
    """The next two cards, or `done` when the quiz is over."""

    pair: tuple[FeedItem, FeedItem] | None
    round: int
    rounds: int
    done: bool


@dataclass(frozen=True)
class _Seed:
    """A verified favourite the quiz can use as a Qloo signal."""

    ref: str
    name: str
    entity_type: EntityType


class QuizService:
    """Pairs for the taste quiz, for their owner's profiles."""

    def __init__(
        self,
        profiles: ProfileService,
        exclusions: ExclusionRepository,
        taste_graph: TasteGraph,
        taste: TasteService,
        feedback: FeedbackService,
        rounds: int,
    ) -> None:
        self._profiles = profiles
        self._exclusions = exclusions
        self._taste_graph = taste_graph
        self._taste = taste
        self._feedback = feedback
        self._rounds = rounds

    async def next(
        self,
        owner_id: UUID,
        profile_id: UUID,
        picked_ref: str | None,
        shown_refs: Sequence[str],
    ) -> QuizStep:
        """Record the pick, if any, and return the next pair or `done`."""
        profile = await self._profiles.get(owner_id, profile_id)
        shown = list(dict.fromkeys(shown_refs))
        if picked_ref is not None and picked_ref not in shown[-2:]:
            raise InvalidInputError("Pick one of the two cards just shown.")
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        entries = [
            entry
            for entry in await self._set(profile, blocklist)
            if not blocklist.blocks(entry.match.entity_id, entry.match.name)
        ]
        by_ref = {entry.match.entity_id: entry for entry in entries}
        picked = by_ref[picked_ref].match if picked_ref in by_ref else None
        if picked is not None:
            await self._feedback.record_for(
                profile.id, ItemRef(picked.entity_id, picked.name, picked.type), Signal.QUIZ_PICK
            )
        rounds_done = len(shown) // 2
        unseen = [entry for entry in entries if entry.match.entity_id not in set(shown)]
        if rounds_done >= self._rounds or len(unseen) < 2:
            return QuizStep(pair=None, round=rounds_done, rounds=self._rounds, done=True)
        if picked is None:
            first = unseen[0]
        else:
            ranked = await self._taste.score([entry.match for entry in unseen], picked)
            first = by_ref[ranked[0].entity_id]
        second = _different(first, [entry for entry in unseen if entry is not first])
        # Alternate sides, so the similar card isn't always on the left.
        pair = (first, second) if rounds_done % 2 == 0 else (second, first)
        country = profile.country_code
        return QuizStep(
            pair=(_card(pair[0], country), _card(pair[1], country)),
            round=rounds_done + 1,
            rounds=self._rounds,
            done=False,
        )

    async def _set(self, profile: Profile, blocklist: Blocklist) -> list[QuizEntry]:
        """What to quiz on: Qloo's picks for the newest favourites, or recent popular titles.
        Things the user already loves are never offered back."""
        seeds = _seeds(profile, blocklist)
        loved = {favourite.qloo_id for favourite in profile.favourites if favourite.qloo_id}
        cross = [seed for seed in seeds if seed.entity_type is not EntityType.BOOK][:SEED_SIGNALS]
        books = [seed for seed in seeds if seed.entity_type is EntityType.BOOK][:1]
        if cross:
            entries = await self._from_favourites(cross, books)
        else:
            entries = await self._from_popular(profile.country_code, books)
        return [entry for entry in entries if entry.match.entity_id not in loved]

    async def _from_favourites(self, cross: list[_Seed], books: list[_Seed]) -> list[QuizEntry]:
        """One query per type with the favourites as signals, so every card follows from them.
        Qloo accepts a book as a signal only for books, so a book favourite steers just those."""
        ids = tuple(seed.ref for seed in cross)
        reason = f"Because you like {_names(cross)}."
        book_ids = (books[0].ref,) if books else ids
        book_reason = f"Because you like {books[0].name}." if books else reason
        queries = [
            InsightsQuery(entity_type=entity_type, take=take, signal_entities=signals)
            for entity_type, take, signals in (
                (EntityType.ARTIST, ARTIST_TAKE, ids),
                (EntityType.MOVIE, FILM_TAKE, ids),
                (EntityType.TV_SHOW, TV_TAKE, ids),
                (EntityType.BOOK, BOOK_TAKE, book_ids),
            )
        ]
        found = await asyncio.gather(*(self._insights(query) for query in queries))
        reasons = [reason, reason, reason, book_reason]
        groups = [
            [QuizEntry(match, why) for match in matches]
            for matches, why in zip(found, reasons, strict=True)
        ]
        return _interleave(groups)

    async def _from_popular(self, country_code: str | None, books: list[_Seed]) -> list[QuizEntry]:
        """No taste to follow yet: recent, popular films and TV for the country, books, and
        artists that follow the films (artists need a signal)."""
        recent = date.today().year - RECENT_YEARS
        if books:
            book_query = InsightsQuery(
                entity_type=EntityType.BOOK, take=BOOK_TAKE, signal_entities=(books[0].ref,)
            )
        else:
            book_query = InsightsQuery(
                entity_type=EntityType.BOOK, take=BOOK_TAKE, popularity_min=BOOK_POPULARITY
            )
        films, shows, found_books = await asyncio.gather(
            self._insights(
                InsightsQuery(
                    entity_type=EntityType.MOVIE,
                    take=FILM_TAKE,
                    country_code=country_code,
                    popularity_min=SET_POPULARITY,
                    year_min=recent,
                )
            ),
            self._insights(
                InsightsQuery(
                    entity_type=EntityType.TV_SHOW,
                    take=TV_TAKE,
                    country_code=country_code,
                    popularity_min=SET_POPULARITY,
                    year_min=recent,
                )
            ),
            self._insights(book_query),
        )
        artists: list[EntityMatch] = []
        if films:
            artists = await self._insights(
                InsightsQuery(
                    entity_type=EntityType.ARTIST,
                    take=ARTIST_TAKE,
                    signal_entities=tuple(f.entity_id for f in films[:ARTIST_SIGNALS]),
                )
            )
        return _interleave(
            [
                [QuizEntry(match, POPULAR_REASON) for match in group]
                for group in (artists, films, shows, found_books)
            ]
        )

    async def _insights(self, query: InsightsQuery) -> list[EntityMatch]:
        try:
            return await self._taste_graph.insights(query)
        except UpstreamError:
            logger.warning("Quiz set: Qloo failed for %s", query.entity_type)
            return []


def _seeds(profile: Profile, blocklist: Blocklist) -> list[_Seed]:
    """Verified favourites that aren't excluded, newest first."""
    ordered = sorted(profile.favourites, key=lambda item: item.created_at, reverse=True)
    return [
        _Seed(favourite.qloo_id, favourite.name, entity_type_of(favourite.kind))
        for favourite in ordered
        if favourite.qloo_id
        and not blocklist.blocks(favourite_ref(favourite), favourite.song_title or favourite.name)
    ]


def _names(seeds: Sequence[_Seed]) -> str:
    """Favourite names for a reason line: "A" or "A and B"."""
    return " and ".join(seed.name for seed in seeds)


def _interleave(groups: list[list[QuizEntry]]) -> list[QuizEntry]:
    """One of each type in turn, so the set is varied from the start."""
    ordered: list[QuizEntry] = []
    seen: set[str] = set()
    queues = [list(group) for group in groups]
    while any(queues):
        for queue in queues:
            while queue:
                entry = queue.pop(0)
                if entry.match.entity_id not in seen:
                    seen.add(entry.match.entity_id)
                    ordered.append(entry)
                    break
    return ordered


def _different(anchor: QuizEntry, others: Sequence[QuizEntry]) -> QuizEntry:
    """Another type if there is one, else the next item."""
    return next((entry for entry in others if entry.match.type is not anchor.match.type), others[0])


def _card(entry: QuizEntry, country_code: str | None) -> FeedItem:
    return to_card(candidate_from_match(entry.match, entry.reason), country_code)
