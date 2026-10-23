"""The compose step's prompt and output schema: reasons and conversation prompts for the
caregiver. The LLM sees item titles, types and years, and the first name, birth year and places;
never notes or other personal data."""

import json

from pydantic import BaseModel, Field

from app.application.agent.types import PlanContext
from app.domain.sessions import SessionItem

TEXT_MAX = 240

COMPOSE_SYSTEM = """You write short notes for a caregiver who shares music, film and TV clips \
and books with someone they love. For each item, write:
- reason: one plain sentence (at most 25 words) telling the caregiver why it was picked, based \
on its "because" field and the person's details. Warm and factual.
- prompt: one open, gentle conversation starter the caregiver can say aloud (at most 20 words), \
such as "What does this song bring to mind?". Invite feelings and stories. Never test memory: \
never use "remember" or "recall", and never ask quiz questions.
Never make health or medical claims of any kind. Return one entry per item, with its ref."""


class ComposedItem(BaseModel):
    """The LLM's reason and prompt for one item."""

    ref: str
    reason: str = Field(description="Why it was picked, for the caregiver.")
    prompt: str = Field(description="An open, gentle conversation starter.")


class ComposeOutput(BaseModel):
    """The LLM's answer for the whole session."""

    items: list[ComposedItem]


def compose_prompt(items: list[SessionItem], context: PlanContext) -> str:
    """The person's basics and the items, as JSON."""
    person = {
        "first_name": context.first_name,
        "birth_year": context.birth_year,
        "places": list(context.places),
    }
    rows = [
        {
            "ref": item.ref,
            "title": item.title,
            "type": item.entity_type.value,
            "year": item.release_year,
            "age_at_release": item.age_at_release,
            "because": item.signal,
        }
        for item in items
    ]
    return json.dumps({"person": person, "items": rows}, ensure_ascii=False)
