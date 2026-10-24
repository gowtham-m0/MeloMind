"""Step 6, `decorate` (code): candidates become cards, with reasons, images and platform links,
and the sidebar's taste tags are worked out."""

from app.application.agent.cards import taste_tags, to_card
from app.application.agent.deps import FeedDeps
from app.application.agent.state import FeedState
from app.domain.feed import FeedRow

NODE = "decorate"


async def decorate(state: FeedState, deps: FeedDeps) -> FeedState:
    """Build the hero card, the rows and the taste tags."""
    country = state["context"].country_code
    hero = state.get("hero")
    drafts = state.get("drafts", [])
    rows = [
        FeedRow(
            key=draft["key"],
            title=draft["title"],
            subtitle=draft["subtitle"],
            placement=draft["placement"],
            items=tuple(to_card(c, country, draft["reason"]) for c in draft["candidates"]),
        )
        for draft in drafts
    ]
    everything = ([hero] if hero else []) + [c for draft in drafts for c in draft["candidates"]]
    with_images = sum(1 for row in rows for item in row.items if item.image_url)
    total = sum(len(row.items) for row in rows)
    await deps.log.info(
        NODE, f"Added images for {with_images} of {total} picks, and where to find each."
    )
    return {
        "rows": rows,
        "hero_item": to_card(hero, country) if hero else None,
        "taste_tags": taste_tags(everything),
    }
