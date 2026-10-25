"""Unit tests for the hint ladder, its search limits, and the guards that keep lyrics and journal
text away from Qloo."""

from dataclasses import replace
from uuid import uuid4

import pytest

from app.application.agent.ladder import Hints, accepts, climb, ladder_context
from app.application.agent.nodes.extract_mentions import checked, known_mentions
from app.application.agent.nodes.resolve_mentions import resolve_mentions
from app.application.agent.prompts.extract import ExtractedMention, ExtractOutput
from app.application.agent.prompts.interpret import Interpretation, hints_from, template_hints
from app.application.agent.resolve_state import LinkDeps, Mention
from app.application.agent.types import Candidate, SignalRef
from app.application.rows.rows import JournalRow
from app.domain.feed import ItemSource
from app.domain.feedback import Blocklist, Exclusion
from app.domain.journal import JournalNode, NodeKind
from app.domain.models import EntityType, FavouriteKind
from app.domain.names import name_fits
from app.infrastructure.persistence.memory_journal import InMemoryJournalRepository
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.fakes import RecordingTasteGraph, log_messages, make_context, make_log

pytestmark = pytest.mark.anyio

LYRIC = "sometimes all I think about is you late nights in the middle of June"


def candidate(name: str, entity_type: EntityType, year: int | None = None) -> Candidate:
    return Candidate("id", name, entity_type, ItemSource.DEMO_FIXTURE, "", release_year=year)


def test_names_fit_across_case_initials_articles_and_spellings() -> None:
    assert name_fits("T. M. Soundararajan", "TMS")
    assert name_fits("The 1975", "1975")
    assert name_fits("Arijit Singh", "Arijith Singh")
    assert not name_fits("Inception", "Interstellar")


def test_acceptance_checks_type_name_and_year() -> None:
    film = candidate("To Kill a Mockingbird", EntityType.MOVIE, 1962)

    assert accepts(film, EntityType.MOVIE, "To Kill a Mockingbird", 1962)
    assert not accepts(film, EntityType.BOOK, "To Kill a Mockingbird", None)
    assert not accepts(film, EntityType.MOVIE, "To Kill a Mockingbird", 1990)
    assert accepts(
        candidate("Glass Animals", EntityType.ARTIST), EntityType.ARTIST, "glass animals", 1
    )


def test_a_long_lyric_is_never_a_name() -> None:
    template = template_hints(LYRIC, FavouriteKind.SONG, None)
    guessed = hints_from(Interpretation(kind="song", title=LYRIC, singer=LYRIC), LYRIC, None)

    assert template.title is None and template.singer is None and template.song_title is None
    assert guessed.title is None and guessed.singer is None and guessed.song_title is None


async def test_the_ladder_stops_at_its_search_budget() -> None:
    log, runs = await make_log()
    taste = RecordingTasteGraph(FixtureTasteGraph(), empty_searches=["nobody", "nobody here"])
    ctx = ladder_context(taste, log, uuid4(), Blocklist(), 2, "ladder")
    hints = Hints(
        kind=FavouriteKind.SONG,
        singer="Nobody",
        composer="Nobody Here",
        film="Nothing Film",
        actor="Nobody Else",
    )

    proposals = await climb(ctx, hints)

    assert proposals == []
    assert len(taste.searches) == 2
    assert any("Used all 2 searches" in message for message in await log_messages(runs, log))


async def test_a_song_is_found_by_its_singer_and_its_title_is_never_searched() -> None:
    log, _ = await make_log()
    taste = RecordingTasteGraph(FixtureTasteGraph())
    ctx = ladder_context(taste, log, uuid4(), Blocklist(), 5, "ladder", song_titles=("Heat Waves",))
    hints = Hints(kind=FavouriteKind.SONG, song_title="Heat Waves", singer="Glass Animals")

    proposals = await climb(ctx, hints)

    assert [(p.name, p.kind, p.song_title) for p in proposals] == [
        ("Glass Animals", FavouriteKind.SONG, "Heat Waves")
    ]
    assert taste.searches == ["Glass Animals"]


async def test_the_ladder_never_proposes_an_excluded_item() -> None:
    log, _ = await make_log()
    profile_id = uuid4()
    blocked = Blocklist.from_exclusions(
        [Exclusion(profile_id, "demo-artist-glass-animals", "Glass Animals")]
    )
    ctx = ladder_context(FixtureTasteGraph(), log, profile_id, blocked, 5, "ladder")

    proposals = await climb(ctx, Hints(kind=FavouriteKind.ARTIST, singer="Glass Animals"))

    assert proposals == []


def test_extracted_mentions_must_be_in_the_text_and_sure_enough() -> None:
    text = "Watched Interstellar with my brother Arjun."
    answer = ExtractOutput(
        mentions=[
            ExtractedMention(kind="movie", text="Interstellar", confidence=0.9),
            ExtractedMention(kind="movie", text="Inception", confidence=0.9),
            ExtractedMention(kind="artist", text="Arjun", confidence=0.3),
            ExtractedMention(kind="movie", text="interstellar", confidence=0.8),
        ]
    )

    assert [m.text for m in checked(answer, text)] == ["Interstellar"]


def test_the_rule_based_reader_spots_known_names_only() -> None:
    known = [("artist", "Glass Animals"), ("movie", "Her"), ("book", "Circe")]

    found = known_mentions("Glass Animals all evening. Where is her book?", known)

    assert [(m.kind, m.text) for m in found] == [("artist", "Glass Animals"), ("movie", "Her")]


async def test_a_link_run_stops_at_its_search_budget() -> None:
    log, runs = await make_log()
    taste = RecordingTasteGraph(FixtureTasteGraph())
    profile_id = uuid4()
    entry = JournalNode(profile_id=profile_id, kind=NodeKind.ENTRY, title="today", body="...")
    deps = LinkDeps(
        taste=taste,
        journal=InMemoryJournalRepository(),
        log=log,
        profile_id=profile_id,
        blocklist=Blocklist(),
        max_searches=10,
    )
    # Each unknown name costs two searches: as typed, then another spelling ("Rahim").
    mentions = [Mention(kind="artist", text=f"Raheem {n}") for n in range(9)]

    result = await resolve_mentions({"entry": entry, "mentions": mentions}, deps)

    assert len(taste.searches) == 10
    assert all(match is None for _, match in result["resolved"])
    assert len(result["resolved"]) == 5
    assert any("Out of searches" in message for message in await log_messages(runs, log))


def test_the_journal_row_needs_a_confirmed_item_and_crosses_types() -> None:
    row = JournalRow()
    film = SignalRef("demo-movie-interstellar", "Interstellar", EntityType.MOVIE, learned=True)
    empty = make_context()
    context = replace(make_context(), journal_signals=(film,))

    specs = row.specs(context, [])

    assert not row.applies(empty) and row.applies(context)
    assert [query.entity_type for query in specs[0].queries] == [
        EntityType.MOVIE,
        EntityType.ARTIST,
    ]
    assert specs[0].subtitle == "Because you wrote about Interstellar"
