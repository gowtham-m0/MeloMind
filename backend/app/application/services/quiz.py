"""The onboarding taste quiz ("this or that"): two big cards at a time from a set of popular,
varied items for the user's country.

The first pair is two different types. After each pick, the next pair is the unseen item most
like the pick (Qloo scores the set), plus one of another type to keep exploring. Each pick is a
`quiz_pick` signal; the card not picked gets nothing, because not choosing isn't disliking.
"""

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from app.application.agent.cards import candidate_from_match, to_card
from app.application.ports import EntityMatch, ExclusionRepository, InsightsQuery, TasteGraph
from app.application.services.feedback import FeedbackService, ItemRef
from app.application.services.profiles import ProfileService
from app.application.services.taste import TasteService
from app.core.errors import InvalidInputError, UpstreamError
from app.domain.feed import FeedItem
from app.domain.feedback import Blocklist, Signal
from app.domain.models import EntityType

logger = logging.getLogger(__name__)

QUIZ_REASON = "popular right now"
FILM_TAKE = 8
TV_TAKE = 6
BOOK_TAKE = 4
ARTIST_TAKE = 6
SET_POPULARITY = 0.8
BOOK_POPULARITY = 0.6
ARTIST_SIGNALS = 3


@dataclass(frozen=True)
class QuizStep:
    """The next two cards, or `done` when the quiz is over."""

    pair: tuple[FeedItem, FeedItem] | None
    round: int
    rounds: int
    done: bool


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
        pool = [
            m
            for m in await self._set(profile.country_code)
            if not blocklist.blocks(m.entity_id, m.name)
        ]
        by_ref = {match.entity_id: match for match in pool}
        picked = by_ref.get(picked_ref) if picked_ref else None
        if picked is not None:
            await self._feedback.record_for(
                profile.id, ItemRef(picked.entity_id, picked.name, picked.type), Signal.QUIZ_PICK
            )
        rounds_done = len(shown) // 2
        unseen = [match for match in pool if match.entity_id not in set(shown)]
        if rounds_done >= self._rounds or len(unseen) < 2:
            return QuizStep(pair=None, round=rounds_done, rounds=self._rounds, done=True)
        if picked is None:
            first = unseen[0]
        else:
            ranked = await self._taste.score(unseen, picked)
            first = by_ref[ranked[0].entity_id]
        second = _different(first, [match for match in unseen if match is not first])
        # Alternate sides, so the similar card isn't always on the left.
        pair = (first, second) if rounds_done % 2 == 0 else (second, first)
        country = profile.country_code
        return QuizStep(
            pair=(_card(pair[0], country), _card(pair[1], country)),
            round=rounds_done + 1,
            rounds=self._rounds,
            done=False,
        )

    async def _set(self, country_code: str | None) -> list[EntityMatch]:
        """Popular films and TV for the country, popular books, and artists that follow the
        films (artists need a signal). Every query is cached, so this is cheap after once."""
        films = await self._insights(
            InsightsQuery(
                entity_type=EntityType.MOVIE,
                take=FILM_TAKE,
                country_code=country_code,
                popularity_min=SET_POPULARITY,
            )
        )
        shows = await self._insights(
            InsightsQuery(
                entity_type=EntityType.TV_SHOW,
                take=TV_TAKE,
                country_code=country_code,
                popularity_min=SET_POPULARITY,
            )
        )
        books = await self._insights(
            InsightsQuery(
                entity_type=EntityType.BOOK, take=BOOK_TAKE, popularity_min=BOOK_POPULARITY
            )
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
        return _interleave([artists, films, shows, books])

    async def _insights(self, query: InsightsQuery) -> list[EntityMatch]:
        try:
            return await self._taste_graph.insights(query)
        except UpstreamError:
            logger.warning("Quiz set: Qloo failed for %s", query.entity_type)
            return []


def _interleave(groups: list[list[EntityMatch]]) -> list[EntityMatch]:
    """One of each type in turn, so the set is varied from the start."""
    ordered: list[EntityMatch] = []
    seen: set[str] = set()
    queues = [list(group) for group in groups]
    while any(queues):
        for queue in queues:
            while queue:
                match = queue.pop(0)
                if match.entity_id not in seen:
                    seen.add(match.entity_id)
                    ordered.append(match)
                    break
    return ordered


def _different(anchor: EntityMatch, others: Sequence[EntityMatch]) -> EntityMatch:
    """Another type if there is one, else the next item."""
    return next((match for match in others if match.type is not anchor.type), others[0])


def _card(match: EntityMatch, country_code: str | None) -> FeedItem:
    return to_card(candidate_from_match(match, QUIZ_REASON), country_code)
