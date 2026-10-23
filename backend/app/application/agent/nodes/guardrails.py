"""Step 6, `guardrails` (code only, never an LLM): the rules every session must meet.

In order (docs/AGENT.md, section 9):
1. Remove blocked items (rejected or upset), by ID, and `fav:` items also by name.
2. Remove items without a source or a reason basis.
3. Remove items with no playable video (books excepted), refilling from playable spares of the
   same type, then any playable spare. A book never stands in for music, film or TV.
4. Fit the target length ± 10 %: drop the lowest-ranked item while too long (from a type with
   more than one, to keep the mix), add spares while too short. Modes without a length (the
   warm-up) are capped at their mix size instead.
"""

from collections import Counter
from dataclasses import dataclass, field

from app.application.agent.deps import PlanDeps
from app.application.agent.nodes.resolve_media import ready
from app.application.agent.state import PlanState
from app.application.agent.types import PlannedItem
from app.domain.feedback import Blocklist
from app.domain.policies import target_bounds
from app.domain.sessions import SessionItem

NODE = "guardrails"


@dataclass
class GuardrailResult:
    """The session's items, in order, and what the guardrails changed."""

    items: list[SessionItem]
    notes: list[str] = field(default_factory=list)


def apply_guardrails(
    planned: list[PlannedItem],
    spares: list[PlannedItem],
    blocklist: Blocklist,
    *,
    target_minutes: int | None,
    max_items: int,
) -> GuardrailResult:
    """Apply guardrails 1–4. `target_minutes` None means no length to fit."""
    notes: list[str] = []
    kept, pool = _remove_blocked(planned, spares, blocklist, notes)
    sourced = [entry for entry in kept if _has_basis(entry.item)]
    if len(sourced) < len(kept):
        notes.append(f"Removed {len(kept) - len(sourced)} items with no source.")
    pool = [entry for entry in pool if _has_basis(entry.item)]
    kept = _refill_unplayable(sourced, pool, notes)
    # Only videos fill gaps: the session's one book is a conversation slot, not filler.
    pool = [entry for entry in pool if entry.item.playable]
    if target_minutes is None:
        kept = kept[:max_items]
    else:
        kept = _fit_length(kept, pool, target_minutes, notes)
    items = [entry.item for entry in kept]
    for position, item in enumerate(items):
        item.position = position
    return GuardrailResult(items=items, notes=notes)


def _remove_blocked(
    planned: list[PlannedItem], spares: list[PlannedItem], blocklist: Blocklist, notes: list[str]
) -> tuple[list[PlannedItem], list[PlannedItem]]:
    kept = [entry for entry in planned if not blocklist.blocks(entry.item.ref, entry.item.title)]
    pool = [entry for entry in spares if not blocklist.blocks(entry.item.ref, entry.item.title)]
    removed = len(planned) - len(kept)
    if removed:
        notes.append(f"Removed {removed} blocked item{'s' if removed > 1 else ''}.")
    return kept, pool


def _has_basis(item: SessionItem) -> bool:
    """Rule 9: every item records where it came from and what led to it."""
    return bool(item.ref and item.source and item.signal.strip())


def _refill_unplayable(
    kept: list[PlannedItem], pool: list[PlannedItem], notes: list[str]
) -> list[PlannedItem]:
    result: list[PlannedItem] = []
    for entry in kept:
        if ready(entry):
            result.append(entry)
            continue
        playable = [spare for spare in pool if spare.item.playable]
        same_type = [s for s in playable if s.item.entity_type is entry.item.entity_type]
        swap = (same_type or playable or [None])[0]
        if swap is None:
            notes.append(f"Removed {entry.item.title}: no playable version found.")
            continue
        pool.remove(swap)
        result.append(swap)
        notes.append(f"Swapped {entry.item.title} for {swap.item.title}, which can play.")
    return result


def _fit_length(
    kept: list[PlannedItem], pool: list[PlannedItem], target_minutes: int, notes: list[str]
) -> list[PlannedItem]:
    low, high = target_bounds(target_minutes)
    kept = list(kept)
    pool = sorted(pool, key=lambda entry: entry.rank)
    total = sum(entry.item.duration_s for entry in kept)
    while total > high and len(kept) > 1:
        worst = _droppable(kept)
        kept.remove(worst)
        total -= worst.item.duration_s
        notes.append(f"Left out {worst.item.title} to fit {target_minutes} minutes.")
    while total < low and pool:
        fitting = [entry for entry in pool if total + entry.item.duration_s <= high]
        choice = fitting[0] if fitting else min(pool, key=lambda entry: entry.item.duration_s)
        if not fitting and total + choice.item.duration_s - high >= low - total:
            break
        pool.remove(choice)
        kept.append(choice)
        total += choice.item.duration_s
        notes.append(f"Added {choice.item.title} to fill the time.")
    return kept


def _droppable(kept: list[PlannedItem]) -> PlannedItem:
    """The lowest-ranked item of a type that has more than one, so the mix keeps its variety."""
    counts = Counter(entry.item.entity_type for entry in kept)
    doubled = [entry for entry in kept if counts[entry.item.entity_type] > 1]
    return max(doubled or kept, key=lambda entry: entry.rank)


async def guardrails(state: PlanState, deps: PlanDeps) -> PlanState:
    """Apply the guardrails and log each change."""
    context = state["context"]
    result = apply_guardrails(
        state.get("planned", []),
        state.get("ready_spares", []),
        context.blocklist,
        target_minutes=deps.target_minutes if deps.mode.fits_length else None,
        max_items=sum(count for _, count in deps.mode.mix),
    )
    for note in result.notes:
        await deps.log.info(NODE, note)
    if not any(item.playable for item in result.items):
        # Books alone aren't a session: without a single video there's nothing to play.
        await deps.log.warn(NODE, "No item has a playable video, so there's no session to offer.")
        return {"items": []}
    total = sum(item.duration_s for item in result.items)
    await deps.log.info(
        NODE, f"Checked {len(result.items)} items: {total // 60} min {total % 60} s in all."
    )
    return {"items": result.items}
