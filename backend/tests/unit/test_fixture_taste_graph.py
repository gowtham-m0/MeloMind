"""Tests for FixtureTasteGraph: search and insights over the demo fixtures."""

import pytest

from app.application.ports import InsightsQuery
from app.domain.models import EntityType
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph

pytestmark = pytest.mark.anyio

SUPREMES = "demo-artist-the-supremes"
TEMPTATIONS = "demo-artist-the-temptations"


@pytest.fixture(scope="module")
def graph() -> FixtureTasteGraph:
    return FixtureTasteGraph()


async def test_search_matches_aliases_and_returns_the_canonical_name(
    graph: FixtureTasteGraph,
) -> None:
    matches = await graph.search("TMS", (EntityType.ARTIST,))

    assert [match.name for match in matches] == ["T. M. Soundararajan"]
    assert matches[0].source == "demo_fixture"


async def test_search_ignores_case_and_punctuation(graph: FixtureTasteGraph) -> None:
    matches = await graph.search("p susheela")

    assert matches[0].name == "P. Susheela"


async def test_search_filters_by_type(graph: FixtureTasteGraph) -> None:
    books = await graph.search("To Kill a Mockingbird", (EntityType.BOOK,))
    films = await graph.search("To Kill a Mockingbird", (EntityType.MOVIE,))

    assert [(match.type, match.release_year) for match in books] == [(EntityType.BOOK, 1960)]
    assert [(match.type, match.release_year) for match in films] == [(EntityType.MOVIE, 1962)]


async def test_search_puts_exact_matches_first_and_honours_take(graph: FixtureTasteGraph) -> None:
    matches = await graph.search("the", take=3)

    assert len(matches) == 3
    assert await graph.search("") == []


async def test_insights_returns_related_items_of_one_type_by_affinity(
    graph: FixtureTasteGraph,
) -> None:
    matches = await graph.insights(
        InsightsQuery(EntityType.ARTIST, take=5, signal_entities=(SUPREMES,))
    )

    assert len(matches) == 5
    assert all(match.type is EntityType.ARTIST for match in matches)
    assert SUPREMES not in [match.entity_id for match in matches]
    affinities = [match.affinity or 0 for match in matches]
    assert affinities == sorted(affinities, reverse=True)
    assert matches[0].entity_id == TEMPTATIONS


async def test_insights_applies_exclusions(graph: FixtureTasteGraph) -> None:
    matches = await graph.insights(
        InsightsQuery(
            EntityType.ARTIST, take=20, signal_entities=(SUPREMES,), exclude_entities=(TEMPTATIONS,)
        )
    )

    assert TEMPTATIONS not in [match.entity_id for match in matches]


async def test_insights_applies_era_country_and_popularity_to_films(
    graph: FixtureTasteGraph,
) -> None:
    matches = await graph.insights(
        InsightsQuery(
            EntityType.MOVIE,
            take=50,
            age_55_plus=True,
            year_min=1961,
            year_max=1969,
            country_code="us",
            popularity_min=0.7,
        )
    )

    assert matches
    for match in matches:
        assert match.release_year is not None and 1961 <= match.release_year <= 1969
        assert match.popularity is not None and match.popularity >= 0.7
        assert match.affinity is None
    names = [match.name for match in matches]
    assert "Kadhalikka Neramillai" not in names


async def test_insights_ignores_era_for_artists(graph: FixtureTasteGraph) -> None:
    with_era = await graph.insights(
        InsightsQuery(EntityType.ARTIST, take=50, year_min=2000, year_max=2001)
    )

    assert with_era


async def test_insights_scores_only_the_given_set(graph: FixtureTasteGraph) -> None:
    score_set = (TEMPTATIONS, "demo-artist-p-susheela")
    matches = await graph.insights(
        InsightsQuery(
            EntityType.ARTIST, take=10, signal_entities=(SUPREMES,), score_entities=score_set
        )
    )

    assert {match.entity_id for match in matches} <= set(score_set)
    assert matches[0].entity_id == TEMPTATIONS
    assert all(match.affinity is not None for match in matches)


def test_insights_query_rejects_take_out_of_range() -> None:
    with pytest.raises(ValueError, match="take"):
        InsightsQuery(EntityType.MOVIE, take=0)
