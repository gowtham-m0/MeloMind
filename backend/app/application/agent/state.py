"""The plan_session workflow's state. Each node reads some keys and writes others."""

from typing import TypedDict

from app.application.agent.types import (
    Candidate,
    PlanContext,
    PlannedItem,
    ResearchBrief,
    ResearchOutcome,
)
from app.domain.models import Profile
from app.domain.sessions import SessionItem


class PlanState(TypedDict, total=False):
    """Written by: `profile` (start), `context` (load_context), `brief`, `candidates`,
    `research_outcome` (research, fallback), `fallback_attempts` (fallback), `ranks`,
    `selected`, `spares` (select_items), `planned`, `ready_spares`, `media_errors`
    (resolve_media), `items` (guardrails, compose)."""

    profile: Profile
    context: PlanContext
    brief: ResearchBrief
    candidates: list[Candidate]
    research_outcome: ResearchOutcome
    fallback_attempts: int
    ranks: dict[str, int]
    selected: list[Candidate]
    spares: list[Candidate]
    planned: list[PlannedItem]
    ready_spares: list[PlannedItem]
    media_errors: int
    items: list[SessionItem]
