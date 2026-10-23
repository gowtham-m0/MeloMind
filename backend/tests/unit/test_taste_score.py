"""Tests for TasteService.score: Qloo scores the warm-up set, or it falls back to the same type
and the closest year."""

import pytest

from app.application.ports import EntityMatch, InsightsQuery
from app.application.services.taste import TasteService
from app.domain.models import EntityType
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import FailingTasteGraph, RecordingTasteGraph

pytestmark = pytest.mark.anyio


def match(entity_id: str, entity_type: EntityType, year: int | None) -> EntityMatch:
    return EntityMatch(entity_id, entity_id, entity_type, "demo_fixture", release_year=year)


SUPREMES = match("demo-artist-the-supremes", EntityType.ARTIST, 1964)
CANDIDATES = [
    match("demo-movie-mary-poppins", EntityType.MOVIE, 1964),
    match("demo-artist-the-beatles", EntityType.ARTIST, 1963),
    match("demo-artist-the-temptations", EntityType.ARTIST, 1964),
    match("demo-artist-elvis-presley", EntityType.ARTIST, 1956),
]


async def test_qloo_scores_the_same_type_candidates_with_one_call() -> None:
    recorder = RecordingTasteGraph(FixtureTasteGraph())

    ranked = await TasteService(recorder).score(CANDIDATES, SUPREMES)

    [query] = recorder.insights_queries
    assert query.signal_entities == (SUPREMES.entity_id,)
    assert set(query.score_entities) == {
        "demo-artist-the-beatles",
        "demo-artist-the-temptations",
        "demo-artist-elvis-presley",
    }
    assert ranked[0].entity_id == "demo-artist-the-temptations"
    assert ranked[0].affinity == 0.97
    assert ranked[-1].entity_id == "demo-movie-mary-poppins"


async def test_it_falls_back_to_the_same_type_and_closest_year_when_qloo_fails() -> None:
    ranked = await TasteService(FailingTasteGraph()).score(CANDIDATES, SUPREMES)

    assert [m.entity_id for m in ranked] == [
        "demo-artist-the-temptations",
        "demo-artist-the-beatles",
        "demo-artist-elvis-presley",
        "demo-movie-mary-poppins",
    ]


class EmptyGraph(RecordingTasteGraph):
    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        self.insights_queries.append(query)
        return []


async def test_it_falls_back_when_qloo_returns_nothing_or_the_signal_is_a_typed_favourite() -> None:
    empty = EmptyGraph(FixtureTasteGraph())
    typed = match("fav:123", EntityType.ARTIST, 1964)

    from_empty = await TasteService(empty).score(CANDIDATES, SUPREMES)
    from_typed = await TasteService(empty).score(CANDIDATES, typed)

    assert from_empty[0].entity_id == "demo-artist-the-temptations"
    assert from_typed[0].entity_id == "demo-artist-the-temptations"
    assert len(empty.insights_queries) == 1
