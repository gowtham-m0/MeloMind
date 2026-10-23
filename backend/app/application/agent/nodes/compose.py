"""Step 7, `compose` (LLM, with a template fallback): a reason and a conversation prompt for each
item. Then guardrail 5, in code: any line that tests memory or makes a health claim is replaced
by a template. Modes without prompts (the warm-up) skip the LLM."""

import asyncio
import logging

from app.application.agent.deps import PlanDeps
from app.application.agent.prompts.compose import (
    COMPOSE_SYSTEM,
    TEXT_MAX,
    ComposeOutput,
    compose_prompt,
)
from app.application.agent.prompts.templates import template_prompt, template_reason
from app.application.agent.state import PlanState
from app.application.agent.types import PlanContext
from app.domain.policies import is_memory_test, makes_medical_claim
from app.domain.sessions import SessionItem

logger = logging.getLogger(__name__)

NODE = "compose"
COMPOSE_TIMEOUT_SECONDS = 15.0


async def compose(state: PlanState, deps: PlanDeps) -> PlanState:
    """Write reasons and prompts, then check every line in code."""
    context = state["context"]
    items = state.get("items", [])
    if not deps.mode.writes_prompts:
        for item in items:
            item.reason = _clean(item.reason) or template_reason(item, context)
            item.prompt = None
        await deps.log.info(NODE, "Wrote short reasons. No prompts: Person mode never shows them.")
    elif deps.language_model is None:
        _use_templates(items, context)
        await deps.log.info(
            NODE, "No AI model is set up; wrote reasons and prompts from templates."
        )
    else:
        await _compose_with_llm(items, context, deps)
    replaced = _check_lines(items, context)
    if replaced:
        await deps.log.info(
            NODE, f"Replaced {replaced} line(s) that tested memory or sounded medical."
        )
    return {"items": items}


async def _compose_with_llm(items: list[SessionItem], context: PlanContext, deps: PlanDeps) -> None:
    if deps.language_model is None:
        return
    try:
        answer = await asyncio.wait_for(
            deps.language_model.structured(
                COMPOSE_SYSTEM, compose_prompt(items, context), ComposeOutput
            ),
            COMPOSE_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("Compose failed: %s", type(exc).__name__)
        _use_templates(items, context)
        await deps.log.warn(NODE, "The AI didn't answer in time; used templates.")
        return
    by_ref = {entry.ref: entry for entry in answer.items}
    missing = 0
    for item in items:
        entry = by_ref.get(item.ref)
        reason = _clean(entry.reason) if entry else ""
        prompt = _clean(entry.prompt) if entry else ""
        if not reason or not prompt:
            missing += 1
        item.reason = reason or template_reason(item, context)
        item.prompt = prompt or template_prompt(item)
    await deps.log.info(NODE, "Wrote reasons and prompts.")
    if missing:
        await deps.log.info(NODE, f"Used templates for {missing} item(s) the AI left out.")


def _use_templates(items: list[SessionItem], context: PlanContext) -> None:
    """Template prompts, and template reasons where the agent gave no reason of its own."""
    for item in items:
        item.reason = _clean(item.reason) or template_reason(item, context)
        item.prompt = template_prompt(item)


def _check_lines(items: list[SessionItem], context: PlanContext) -> int:
    """Guardrail 5. Returns how many lines were replaced."""
    replaced = 0
    for item in items:
        if makes_medical_claim(item.reason):
            template = template_reason(item, context)
            replaced += template != item.reason
            item.reason = template
        if item.prompt is not None and (
            is_memory_test(item.prompt) or makes_medical_claim(item.prompt)
        ):
            template = template_prompt(item)
            replaced += template != item.prompt
            item.prompt = template
    return replaced


def _clean(text: str) -> str:
    """One line, at most `TEXT_MAX` characters, cut at a word."""
    line = " ".join(text.split())
    if len(line) <= TEXT_MAX:
        return line
    return line[:TEXT_MAX].rsplit(" ", 1)[0].rstrip(",;:") + "…"
