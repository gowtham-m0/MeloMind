"""Feed items and rows to and from JSON, for the `feeds` and `catalog_items` JSONB columns and
for an ask run's result."""

from typing import Any

from app.domain.feed import FeedItem, FeedRow, ItemSource, PlatformLink
from app.domain.models import EntityType


def item_to_json(item: FeedItem) -> dict[str, Any]:
    """A card as plain JSON."""
    return {
        "ref": item.ref,
        "title": item.title,
        "entity_type": item.entity_type.value,
        "source": item.source.value,
        "reason": item.reason,
        "because_of_ref": item.because_of_ref,
        "because_of_title": item.because_of_title,
        "year": item.year,
        "image_url": item.image_url,
        "affinity": item.affinity,
        "popularity": item.popularity,
        "tags": list(item.tags),
        "description": item.description,
        "links": [
            {"platform": link.platform, "label": link.label, "url": link.url, "kind": link.kind}
            for link in item.links
        ],
        "creator": item.creator,
        "parent_ref": item.parent_ref,
        "parent_title": item.parent_title,
        "preview_url": item.preview_url,
    }


def item_from_json(data: dict[str, Any]) -> FeedItem:
    """A card from its JSON."""
    return FeedItem(
        ref=data["ref"],
        title=data["title"],
        entity_type=EntityType(data["entity_type"]),
        source=ItemSource(data["source"]),
        reason=data["reason"],
        because_of_ref=data.get("because_of_ref"),
        because_of_title=data.get("because_of_title"),
        year=data.get("year"),
        image_url=data.get("image_url"),
        affinity=data.get("affinity"),
        popularity=data.get("popularity"),
        tags=tuple(data.get("tags") or ()),
        description=data.get("description"),
        links=tuple(
            PlatformLink(
                platform=link["platform"], label=link["label"], url=link["url"], kind=link["kind"]
            )
            for link in data.get("links") or ()
        ),
        creator=data.get("creator"),
        parent_ref=data.get("parent_ref"),
        parent_title=data.get("parent_title"),
        preview_url=data.get("preview_url"),
    )


def row_to_json(row: FeedRow) -> dict[str, Any]:
    """A row as plain JSON."""
    return {
        "key": row.key,
        "title": row.title,
        "subtitle": row.subtitle,
        "placement": row.placement,
        "items": [item_to_json(item) for item in row.items],
    }


def row_from_json(data: dict[str, Any]) -> FeedRow:
    """A row from its JSON."""
    return FeedRow(
        key=data["key"],
        title=data["title"],
        subtitle=data.get("subtitle", ""),
        placement=data.get("placement", "main"),
        items=tuple(item_from_json(item) for item in data.get("items") or ()),
    )
