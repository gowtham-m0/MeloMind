"""Tests for the guardrails: blocked items, sources, playability and session length."""

from uuid import uuid4

from app.application.agent.nodes.guardrails import apply_guardrails
from app.application.agent.types import PlannedItem
from app.domain.feedback import Blocklist, Exclusion, ExclusionKind
from app.domain.models import EntityType
from app.domain.policies import BOOK_TALK_SECONDS, target_bounds
from app.domain.sessions import ItemSource, MediaRef, SessionItem


def planned(
    ref: str,
    rank: int,
    entity_type: EntityType = EntityType.ARTIST,
    duration_s: int = 180,
    *,
    playable: bool = True,
    signal: str = "similar to The Supremes",
) -> PlannedItem:
    media = MediaRef("youtube", f"v-{ref}", duration_s, ref) if playable else None
    if entity_type is EntityType.BOOK:
        media, duration_s = None, BOOK_TALK_SECONDS
    item = SessionItem(
        ref=ref,
        title=ref.title(),
        entity_type=entity_type,
        source=ItemSource.DEMO_FIXTURE,
        signal=signal,
        media=media,
        duration_s=duration_s if media or entity_type is EntityType.BOOK else 0,
    )
    return PlannedItem(item=item, rank=rank)


def refs(items: list[SessionItem]) -> list[str]:
    return [item.ref for item in items]


def test_blocked_items_never_pass_even_as_spares() -> None:
    blocklist = Blocklist.from_exclusions(
        [
            Exclusion(uuid4(), "a", "A", ExclusionKind.REJECTED),
            Exclusion(uuid4(), "s", "S", ExclusionKind.HIDDEN),
        ]
    )

    result = apply_guardrails(
        [planned("a", 0), planned("b", 1)],
        [planned("s", 2)],
        blocklist,
        target_minutes=None,
        max_items=12,
    )

    assert refs(result.items) == ["b"]
    assert result.notes == ["Removed 1 blocked item."]


def test_every_item_needs_a_source_and_a_basis() -> None:
    result = apply_guardrails(
        [planned("a", 0), planned("b", 1, signal=" ")],
        [],
        Blocklist(),
        target_minutes=None,
        max_items=12,
    )

    assert refs(result.items) == ["a"]
    assert all(item.source and item.signal for item in result.items)


def test_unplayable_items_are_refilled_from_the_same_type_first() -> None:
    result = apply_guardrails(
        [planned("film", 0, EntityType.MOVIE, playable=False), planned("song", 1)],
        [planned("spare-song", 2), planned("spare-film", 3, EntityType.MOVIE)],
        Blocklist(),
        target_minutes=None,
        max_items=12,
    )

    assert refs(result.items) == ["spare-film", "song"]


def test_unplayable_items_without_a_spare_are_removed_but_books_stay() -> None:
    result = apply_guardrails(
        [planned("book", 0, EntityType.BOOK), planned("song", 1, playable=False)],
        [],
        Blocklist(),
        target_minutes=None,
        max_items=12,
    )

    assert refs(result.items) == ["book"]
    assert result.items[0].duration_s == BOOK_TALK_SECONDS


def test_too_long_drops_the_lowest_ranked_but_keeps_one_of_each_type() -> None:
    items = [planned(f"song{i}", i, duration_s=240) for i in range(6)]
    items.append(planned("show", 9, EntityType.TV_SHOW, duration_s=240))

    result = apply_guardrails(items, [], Blocklist(), target_minutes=20, max_items=12)

    low, high = target_bounds(20)
    total = sum(item.duration_s for item in result.items)
    assert low <= total <= high
    assert "show" in refs(result.items)
    assert "song5" not in refs(result.items)


def test_too_short_adds_spares_that_fit() -> None:
    result = apply_guardrails(
        [planned(f"song{i}", i, duration_s=200) for i in range(4)],
        [planned("long", 4, duration_s=600), planned("a", 5), planned("b", 6), planned("c", 7)],
        Blocklist(),
        target_minutes=20,
        max_items=12,
    )

    low, high = target_bounds(20)
    total = sum(item.duration_s for item in result.items)
    assert low <= total <= high
    assert [item.position for item in result.items] == list(range(len(result.items)))


def test_a_mode_without_a_length_is_capped_at_its_size() -> None:
    result = apply_guardrails(
        [planned(f"s{i}", i) for i in range(15)], [], Blocklist(), target_minutes=None, max_items=12
    )

    assert len(result.items) == 12
