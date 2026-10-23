"""Step 4, `select_items` (code): rank by Qloo affinity, then learned weight, then popularity,
and let the mode pick its mix plus spares."""

from collections import Counter

from app.application.agent.deps import PlanDeps
from app.application.agent.state import PlanState
from app.application.agent.tools.context import count_noun
from app.domain.policies import rank_key

NODE = "select_items"


async def select_items(state: PlanState, deps: PlanDeps) -> PlanState:
    """Rank the candidates and choose the session's items."""
    context = state["context"]
    weights = context.learned_weights
    candidates = [
        candidate
        for candidate in state.get("candidates", [])
        if not context.blocklist.blocks(candidate.entity_id, candidate.name)
    ]
    ranked = sorted(
        candidates,
        key=lambda c: rank_key(c.affinity, weights.get(c.entity_id, 0.0), c.popularity),
    )
    selection = deps.mode.select(ranked, context)
    counts = Counter(candidate.entity_type for candidate in selection.selected)
    picked = ", ".join(
        count_noun(counts[entity_type], entity_type)
        for entity_type, _ in deps.mode.mix
        if counts[entity_type]
    )
    await deps.log.info(NODE, f"Picked {picked or 'nothing'}, plus {len(selection.spares)} spares.")
    boosted = [c.name for c in selection.selected if weights.get(c.entity_id, 0.0) > 0]
    if boosted:
        await deps.log.info(
            NODE, f"Ranked higher because of earlier reactions: {', '.join(boosted)}."
        )
    return {
        "ranks": {candidate.entity_id: rank for rank, candidate in enumerate(ranked)},
        "selected": selection.selected,
        "spares": selection.spares,
    }
