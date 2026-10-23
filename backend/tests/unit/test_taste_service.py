"""Tests for TasteService and the name matching it relies on."""

import pytest

from app.application.services.taste import TasteService
from app.core.errors import InvalidInputError
from app.domain.models import EntityType, FavouriteKind
from app.domain.names import names_match
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
