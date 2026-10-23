"""`find_tags`: genre and region tags, over `TasteGraph.tags`."""

from app.application.agent.tools.context import ToolContext, ToolRefusalError
from app.application.ports import TagMatch
from app.core.errors import UpstreamError

TAGS_TAKE = 5
QUERY_MAX = 60


async def find_tags(ctx: ToolContext, query: str) -> list[TagMatch]:
    """Up to 5 tags whose name matches, such as "Tamil" or "60s"."""
    text = " ".join(query.split())
    if not text or len(text) > QUERY_MAX:
        raise ToolRefusalError(f"Give a tag query of 1 to {QUERY_MAX} characters.")
    await ctx.spend_qloo_call()
    try:
        tags = await ctx.taste.tags(text, TAGS_TAKE)
    except UpstreamError:
        await ctx.log.warn(ctx.node, f"Looked up tags for “{text}” → Qloo didn't answer.")
        raise ToolRefusalError("Qloo didn't answer. Try a different query.") from None
    for tag in tags:
        ctx.tag_names[tag.tag_id] = tag.name
    outcome = f"{len(tags)} found ✓" if tags else "none ✗"
    await ctx.log.info(ctx.node, f"Looked up tags for “{text}” → {outcome}.")
    return tags
