"""`compare_tastes`: the tags two groups of entities share, over `TasteGraph.compare`."""

from app.application.agent.tools.context import ToolContext, ToolRefusalError
from app.application.ports import TagComparison
from app.core.errors import UpstreamError
from app.domain.feed import is_qloo_ref

GROUP_MAX = 5


async def compare_tastes(
    ctx: ToolContext, group_a: tuple[str, ...], group_b: tuple[str, ...]
) -> TagComparison:
    """Compare two groups of 1 to 5 Qloo entity IDs. Qloo answers with tags, never items, and
    every tag found joins the run's tag names so it can be a signal."""
    first, second = _clean(group_a), _clean(group_b)
    if not first or not second:
        raise ToolRefusalError("Each side needs 1 to 5 Qloo entity IDs.")
    await ctx.spend_qloo_call()
    try:
        comparison = await ctx.taste.compare(first, second)
    except UpstreamError:
        await ctx.log.warn(ctx.node, "Asked Qloo to compare the two tastes → Qloo didn't answer.")
        raise ToolRefusalError("Qloo didn't answer. Try again later.") from None
    for tag in comparison.a_tags + comparison.b_tags + comparison.shared:
        ctx.tag_names[tag.tag_id] = tag.name
    await ctx.log.info(
        ctx.node,
        f"Asked Qloo to compare the two tastes ({len(first)} and {len(second)} picks) → "
        f"{len(comparison.shared)} shared tags.",
    )
    return comparison


def _clean(ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(ref for ref in dict.fromkeys(ids) if is_qloo_ref(ref))[:GROUP_MAX]
