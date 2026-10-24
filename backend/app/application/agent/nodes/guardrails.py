"""Step 5, `guardrails` (code only): the feed's rules, enforced in code (rules 1, 2 and 3).

1. Remove anything excluded, by ID and, for typed favourites, by name; songs of an excluded
   artist too.
2. Remove anything without a source or a reason basis.
3. Dedupe: an item appears at most once in the feed, hero included, in its earliest row.
4. Drop rows that fell below their minimum, and fill in the hero if it was removed.
"""

from app.application.agent.deps import FeedDeps
from app.application.agent.state import FeedState, RowDraft
from app.application.agent.types import Candidate, FeedContext
from app.domain.models import EntityType

NODE = "guardrails"
FEW_ROWS = 3


def _allowed(candidate: Candidate, context: FeedContext) -> bool:
    if context.blocklist.blocks(candidate.entity_id, candidate.name):
        return False
    # A song goes when its artist was dismissed.
    if candidate.parent_ref and context.blocklist.blocks(
        candidate.parent_ref, candidate.creator or ""
    ):
        return False
    return bool(candidate.source) and bool(candidate.signal.strip())


async def guardrails(state: FeedState, deps: FeedDeps) -> FeedState:
    """Apply the rules to the hero and the rows."""
    context = state["context"]
    hero = state.get("hero")
    removed = 0
    if hero is not None and not _allowed(hero, context):
        hero = None
        removed += 1
    seen: set[str] = {hero.entity_id} if hero else set()
    kept_rows: list[RowDraft] = []
    dropped: list[str] = []
    for draft in state.get("drafts", []):
        kept: list[Candidate] = []
        for candidate in draft["candidates"]:
            if not _allowed(candidate, context):
                removed += 1
                continue
            if candidate.entity_id in seen:
                continue
            seen.add(candidate.entity_id)
            kept.append(candidate)
        if len(kept) < draft["min_items"]:
            dropped.append(draft["title"])
            continue
        kept_rows.append(RowDraft(**{**draft, "candidates": kept}))
    if hero is None:
        hero = _promote(kept_rows)
    if removed:
        await deps.log.info(NODE, f"Removed {removed} items you're not interested in.")
    for title in dropped:
        await deps.log.info(NODE, f"Dropped “{title}”: too few picks left.")
    main_rows = sum(1 for draft in kept_rows if draft["placement"] == "main")
    if main_rows < FEW_ROWS:
        await deps.log.warn(NODE, f"Only {main_rows} rows today; add a few favourites for more.")
    total = sum(len(draft["candidates"]) for draft in kept_rows) + (1 if hero else 0)
    await deps.log.info(NODE, f"Checked the feed: {total} picks in {len(kept_rows)} rows.")
    return {"drafts": kept_rows, "hero": hero}


def _promote(drafts: list[RowDraft]) -> Candidate | None:
    """The first main-row Qloo item with an image becomes the hero, leaving its row. Songs never
    lead the feed: they are lookups, not Qloo's picks."""
    for draft in drafts:
        if draft["placement"] != "main":
            continue
        for index, candidate in enumerate(draft["candidates"]):
            if candidate.entity_type is EntityType.SONG:
                continue
            if candidate.image_url and len(draft["candidates"]) > draft["min_items"]:
                del draft["candidates"][index]
                return candidate
    return None
