"""Tests for storing feeds as JSON: every field survives the round trip."""

from app.domain.feed import FeedItem, FeedRow, ItemSource, PlatformLink
from app.domain.models import EntityType
from app.infrastructure.persistence.feed_json import (
    item_from_json,
    item_to_json,
    row_from_json,
    row_to_json,
)

ITEM = FeedItem(
    ref="m1",
    title="Interstellar",
    entity_type=EntityType.MOVIE,
    source=ItemSource.QLOO_LIVE,
    reason="Because you liked Arrival.",
    because_of_ref="m0",
    because_of_title="Arrival",
    year=2014,
    image_url="https://images.example.test/m1.jpg",
    affinity=0.91,
    popularity=0.97,
    tags=("Science fiction", "Drama"),
    description="Explorers travel through a wormhole.",
    links=(
        PlatformLink("netflix", "Open on Netflix", "https://www.netflix.com/title/1", "direct"),
    ),
)


def test_items_round_trip() -> None:
    assert item_from_json(item_to_json(ITEM)) == ITEM


def test_rows_round_trip() -> None:
    row = FeedRow(key="cross_culture", title="Cross-culture picks", items=(ITEM,), placement="rail")

    assert row_from_json(row_to_json(row)) == row
