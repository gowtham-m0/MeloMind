"""Use cases over the taste graph: finding entities by name for favourites and the demo seed,
and scoring the taste quiz set against what the user just picked."""

import logging
from collections.abc import Sequence
from dataclasses import replace

from app.application.ports import (
    INSIGHTS_TAKE_MAX,
    EntityMatch,
    InsightsQuery,
    TasteGraph,
    TasteSource,
)
from app.core.errors import InvalidInputError, UpstreamError
from app.domain.feed import is_favourite_ref
from app.domain.models import EntityType, FavouriteKind, search_type_for
from app.domain.names import names_match

logger = logging.getLogger(__name__)

SEARCH_TAKE = 8
QUERY_MAX_LENGTH = 100


class TasteService:
    """Searches Qloo (or the demo fixtures). Songs are searched by singer, never by title."""

    def __init__(self, taste_graph: TasteGraph) -> None:
        self._taste_graph = taste_graph

    @property
    def source(self) -> TasteSource:
        """Where results come from: live Qloo or the demo fixtures."""
        return self._taste_graph.source

    async def search(self, query: str, kind: FavouriteKind | None = None) -> list[EntityMatch]:
        """Matches for a name the user typed, of the type the favourite's kind needs."""
        text = " ".join(query.split())
        if not text:
            raise InvalidInputError("Type a name to search for.")
        if len(text) > QUERY_MAX_LENGTH:
            raise InvalidInputError(f"Keep the search under {QUERY_MAX_LENGTH} characters.")
        types: tuple[EntityType, ...] = (search_type_for(kind),) if kind else ()
        return await self._taste_graph.search(text, types, SEARCH_TAKE)

    async def find_by_name(self, name: str, kind: FavouriteKind) -> EntityMatch | None:
        """The match whose name is the same as `name` and whose type fits the kind, if any."""
        matches = await self.search(name, kind)
        return next((match for match in matches if names_match(match.name, name)), None)

    async def score(
        self, candidates: Sequence[EntityMatch], signal: EntityMatch
    ) -> list[EntityMatch]:
        """The candidates, most similar to `signal` first.

        Asks Qloo with the signal as `signal.interests.entities` and `filter.results.entities`
        set to the candidates of the same type (one call). When that isn't possible or returns
        nothing, it falls back to the same type and the closest year. Logs which path ran.
        """
        same_type = [
            candidate
            for candidate in candidates
            if candidate.type is signal.type and not is_favourite_ref(candidate.entity_id)
        ]
        affinities: dict[str, float] = {}
        if same_type and not is_favourite_ref(signal.entity_id):
            query = InsightsQuery(
                entity_type=signal.type,
                take=min(len(same_type), INSIGHTS_TAKE_MAX),
                signal_entities=(signal.entity_id,),
                score_entities=tuple(c.entity_id for c in same_type[:INSIGHTS_TAKE_MAX]),
            )
            try:
                results = await self._taste_graph.insights(query)
            except UpstreamError:
                logger.warning("Quiz scoring: Qloo failed")
                results = []
            affinities = {r.entity_id: r.affinity for r in results if r.affinity is not None}
        logger.info(
            "Quiz scoring used %s", "Qloo" if affinities else "the same type and closest year"
        )

        def similarity(candidate: EntityMatch) -> tuple[bool, float, bool, int]:
            gap = (
                abs(candidate.release_year - signal.release_year)
                if candidate.release_year is not None and signal.release_year is not None
                else 1000
            )
            return (
                candidate.entity_id not in affinities,
                -affinities.get(candidate.entity_id, 0.0),
                candidate.type is not signal.type,
                gap,
            )

        ordered = sorted(candidates, key=similarity)
        return [replace(c, affinity=affinities.get(c.entity_id, c.affinity)) for c in ordered]
