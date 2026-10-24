"""Tests for TasteService and the name matching it relies on."""

import pytest

from app.application.services.taste import TasteService
from app.core.errors import InvalidInputError
from app.domain.models import EntityType, FavouriteKind
from app.domain.names import names_match, spelling_variants
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph

pytestmark = pytest.mark.anyio


@pytest.fixture
def taste() -> TasteService:
    return TasteService(FixtureTasteGraph())


async def test_song_kind_searches_artists(taste: TasteService) -> None:
    matches = await taste.search("The Temptations", FavouriteKind.SONG)

    assert matches[0].name == "The Temptations"
    assert all(match.type is EntityType.ARTIST for match in matches)


@pytest.mark.parametrize("query", ["", "   ", "x" * 101])
async def test_search_rejects_empty_or_long_queries(taste: TasteService, query: str) -> None:
    with pytest.raises(InvalidInputError):
        await taste.search(query)


async def test_find_by_name_needs_the_same_name_and_type(taste: TasteService) -> None:
    book = await taste.find_by_name("To Kill a Mockingbird", FavouriteKind.BOOK)
    partial = await taste.find_by_name("Supremes", FavouriteKind.ARTIST)

    assert book is not None and book.type is EntityType.BOOK
    assert partial is None


def test_names_match_ignores_case_punctuation_and_initial_spacing() -> None:
    assert names_match("T.M. Soundararajan", "t. m. soundararajan")
    assert names_match("P.Susheela", "P. Susheela")
    assert not names_match("Supremes", "The Supremes")


class AcceptsOneSpelling(FixtureTasteGraph):
    """Finds something only for one exact spelling, and records every query it was asked."""

    def __init__(self, accepted: str) -> None:
        super().__init__()
        self.accepted = accepted
        self.queries: list[str] = []

    async def search(self, query, types, take):  # type: ignore[no-untyped-def]
        self.queries.append(query)
        if query != self.accepted:
            return []
        return await super().search("The Temptations", types, take)


async def test_search_tries_other_spellings_when_nothing_is_found() -> None:
    graph = AcceptsOneSpelling("arijit singh")

    matches = await TasteService(graph).search("arijith singh")

    assert matches
    assert graph.queries[0] == "arijith singh"
    assert graph.queries[-1] == "arijit singh"


async def test_search_does_not_try_spellings_when_the_name_matches(taste: TasteService) -> None:
    graph = AcceptsOneSpelling("The Temptations")

    await TasteService(graph).search("The Temptations")

    assert graph.queries == ["The Temptations"]


def test_spelling_variants_cover_common_transliterations() -> None:
    assert "arijit singh" in spelling_variants("arijith singh")
    assert "rahim" in spelling_variants("raheem")
    assert "singh" not in spelling_variants("singh")
    assert spelling_variants("Dune") == []
