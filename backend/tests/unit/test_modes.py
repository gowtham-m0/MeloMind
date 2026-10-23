"""Tests for the session modes: cold-start tiers, fallback queries, relaxing and selection."""

import pytest

from app.application.agent.types import Candidate, SignalRef
from app.application.modes.base import HIGH_POPULARITY, cold_start_tier
from app.application.modes.registry import default_registry
from app.application.modes.standard import StandardMode
from app.application.modes.warmup import WarmupMode
from app.core.errors import InvalidInputError
from app.domain.models import EntityType
from app.domain.sessions import ItemSource
from tests.fakes import MARGARET_FAVOURITES, SUPREMES, make_context

A, M, T, B = EntityType.ARTIST, EntityType.MOVIE, EntityType.TV_SHOW, EntityType.BOOK


def candidate(entity_id: str, entity_type: EntityType, year: int | None = 1965) -> Candidate:
    return Candidate(
        entity_id=entity_id,
        name=entity_id,
        entity_type=entity_type,
        source=ItemSource.DEMO_FIXTURE,
        signal="similar to The Supremes",
        release_year=year,
    )


def test_the_registry_finds_modes_by_name() -> None:
    registry = default_registry()

    assert registry.get("standard").name == "standard"
    assert registry.get("warmup").name == "warmup"
    with pytest.raises(InvalidInputError):
        registry.get("bridge")


def test_tier_a_uses_the_favourites_with_no_age_signal_or_floor() -> None:
    brief = StandardMode().research_brief(make_context(favourites=MARGARET_FAVOURITES))

    assert brief.tier == "A"
    assert brief.signals == MARGARET_FAVOURITES
    assert not brief.use_age_signal
    assert brief.popularity_min is None
    assert brief.era == (1961, 1969)


def test_tier_b_adds_the_age_signal_and_region_tags() -> None:
    context = make_context(favourites=(SUPREMES,), languages=("Tamil", "English"))
    brief = StandardMode().research_brief(context)

    assert brief.tier == "B"
    assert brief.use_age_signal
    assert brief.tag_hints == ("Tamil", "60s")


def test_tier_c_is_the_big_hits_of_their_youth() -> None:
    context = make_context()
    brief = StandardMode().research_brief(context)
    queries = {query.entity_type: query for query in StandardMode().fallback_queries(context)}

    assert cold_start_tier(context) == "C"
    assert brief.popularity_min == HIGH_POPULARITY
    assert queries[M].age_55_plus and queries[M].era == (1961, 1969)
    assert queries[M].popularity_min == HIGH_POPULARITY
    assert queries[A].signal_from is M
    assert queries[A].signal_ids == ()
    assert "60s" in queries[A].tag_queries


def test_learned_items_count_as_a_hint() -> None:
    learned = SignalRef("q", "Bewitched", EntityType.TV_SHOW, learned=True)

    assert cold_start_tier(make_context(learned=(learned,))) == "B"


def test_fallback_queries_cover_the_mix_films_first() -> None:
    queries = StandardMode().fallback_queries(make_context(favourites=MARGARET_FAVOURITES))

    assert [query.entity_type for query in queries] == [M, T, B, A]
    assert all(query.signal_ids == tuple(s.ref for s in MARGARET_FAVOURITES) for query in queries)
    assert queries[-1].take == 12


def test_relax_widens_the_era_then_lowers_the_floor() -> None:
    mode = StandardMode()
    base = mode.fallback_queries(make_context())

    first = mode.relax(base, 1)[0]
    second = mode.relax(base, 2)[0]

    assert first.era == (1956, 1974) and first.popularity_min == HIGH_POPULARITY
    assert second.era == (1951, 1979) and second.popularity_min == 0.5


def test_standard_select_fills_the_mix_interleaved_with_spares_of_each_type() -> None:
    ranked = [candidate(f"a{i}", A) for i in range(6)]
    ranked += [candidate(f"m{i}", M) for i in range(3)]
    ranked += [candidate("t0", T), candidate("t1", T), candidate("b0", B), candidate("b1", B)]

    selection = StandardMode().select(ranked, make_context())

    assert [c.entity_id for c in selection.selected] == [
        "a0",
        "m0",
        "t0",
        "b0",
        "a1",
        "m1",
        "a2",
        "a3",
    ]
    assert {c.entity_type for c in selection.spares} == {A, M, T, B}


def test_gaps_in_the_mix_are_filled_from_other_types() -> None:
    ranked = [candidate(f"a{i}", A) for i in range(8)] + [candidate("m0", M)]

    selection = StandardMode().select(ranked, make_context())

    assert len(selection.selected) == 8


def test_warmup_has_no_books_and_varies_decades() -> None:
    ranked = [candidate("a60", A, 1964), candidate("a61", A, 1965), candidate("a50", A, 1955)]
    ranked += [candidate("b0", B)]

    selection = WarmupMode().select(ranked, make_context())

    assert [c.entity_id for c in selection.selected][:2] == ["a60", "a50"]
    assert all(c.entity_type is not B for c in selection.selected + selection.spares)
    assert WarmupMode().popularity_floor("A") == HIGH_POPULARITY
    assert not WarmupMode().writes_prompts
