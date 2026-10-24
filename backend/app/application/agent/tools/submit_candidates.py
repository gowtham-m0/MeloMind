"""`submit_candidates`: the research agent's final answer."""

from dataclasses import dataclass, replace

from app.application.agent.tools.context import ToolContext

WHY_MAX = 200


@dataclass(frozen=True)
class SubmitResult:
    """How many picks were kept, and the IDs refused because no tool returned them."""

    accepted: int
    total: int
    unknown_ids: tuple[str, ...]
    blocked: int


async def submit_candidates(ctx: ToolContext, picks: list[tuple[str, str]]) -> SubmitResult:
    """Keep each pick that Qloo recommended this run and that isn't blocked (rules 1 and 3).
    A name the agent only searched for is a signal, not a recommendation."""
    accepted, blocked = 0, 0
    unknown: list[str] = []
    for entity_id, why in picks:
        candidate = ctx.seen.get(entity_id) if entity_id in ctx.recommended else None
        if candidate is None:
            unknown.append(entity_id)
            continue
        if ctx.context.blocklist.blocks(candidate.entity_id, candidate.name):
            blocked += 1
            continue
        ctx.submitted[entity_id] = replace(
            candidate, why=" ".join(why.split())[:WHY_MAX], featured=True
        )
        accepted += 1
    message = f"Submitted {accepted} candidates."
    if unknown:
        message += f" Refused {len(unknown)} that Qloo didn't recommend."
    if blocked:
        message += f" Refused {blocked} you're not interested in."
    await ctx.log.info(ctx.node, message)
    return SubmitResult(
        accepted=accepted, total=len(ctx.submitted), unknown_ids=tuple(unknown), blocked=blocked
    )
