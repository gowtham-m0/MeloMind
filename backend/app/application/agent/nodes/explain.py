"""Step 7, `explain` (LLM, with a template fallback): one line on what changed since the last
feed. Card reasons come from the signals in code, so the LLM can't make one up (rule 2)."""

import asyncio
import logging

from app.application.agent.deps import FeedDeps
from app.application.agent.prompts.explain import (
    EXPLAIN_SYSTEM,
    SUMMARY_MAX,
    ExplainOutput,
    explain_prompt,
)
from app.application.agent.prompts.templates import template_summary
from app.application.agent.state import FeedState

logger = logging.getLogger(__name__)

NODE = "explain"
EXPLAIN_TIMEOUT_SECONDS = 15.0
LIKED_SHOWN = 3


async def explain(state: FeedState, deps: FeedDeps) -> FeedState:
    """Write the summary line."""
    context = state["context"]
    hero = state.get("hero_item")
    items = ([hero] if hero else []) + [item for row in state.get("rows", []) for item in row.items]
    refs = {item.ref for item in items}
    first_feed = not context.previous_refs
    new_count = len(refs - context.previous_refs)
    tags = state.get("taste_tags", ())
    template = template_summary(len(items), new_count, tags, context.previous_tags, first_feed)
    # The first feed gets the template: there's nothing to compare yet.
    if deps.language_model is None or not items or first_feed:
        await deps.log.info(NODE, template)
        return {"summary": template}
    liked = [signal.name for signal in context.learned_signals[:LIKED_SHOWN]]
    prompt = explain_prompt(liked, tags, context.previous_tags, new_count, len(items), first_feed)
    try:
        answer = await asyncio.wait_for(
            deps.language_model.structured(EXPLAIN_SYSTEM, prompt, ExplainOutput),
            EXPLAIN_TIMEOUT_SECONDS,
        )
        summary = " ".join(answer.summary.split())
        if len(summary) > SUMMARY_MAX:
            summary = ""
    except Exception as exc:
        logger.warning("Explain failed: %s", type(exc).__name__)
        await deps.log.info(NODE, "The AI summary didn't come back; used a template.")
        summary = ""
    summary = summary or template
    await deps.log.info(NODE, summary)
    return {"summary": summary}
