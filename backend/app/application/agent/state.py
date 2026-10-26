"""The build_feed workflow's state. Each node reads some keys and writes others."""

from typing import TypedDict

from app.application.agent.types import Candidate, FeedContext, ResearchBrief, ResearchOutcome
from app.domain.feed import FeedItem, FeedRow, RowPlacement
from app.domain.models import Profile


class RowDraft(TypedDict):
    """A row while it's being built: candidates, not cards yet."""

    key: str
    title: str
    subtitle: str
    placement: RowPlacement
    reason: str | None
    min_items: int
    candidates: list[Candidate]


class FeedState(TypedDict, total=False):
    """Written by: `profile` (start), `context` (load_context), `brief`, `pool`,
    `research_outcome` (research, fallback), `fallback_attempts` (fallback), `qloo_calls`
    (research, fallback: what they spent of the feed's Qloo budget), `drafts` (build_rows,
    rank, guardrails), `hero` (rank, guardrails), `rows`, `hero_item`, `taste_tags` (decorate),
    `summary` (explain). `single_row` (ask_row) marks an ask run, whose one row stays a row: no
    hero is promoted from it."""

    profile: Profile
    context: FeedContext
    brief: ResearchBrief
    pool: list[Candidate]
    research_outcome: ResearchOutcome
    fallback_attempts: int
    qloo_calls: int
    drafts: list[RowDraft]
    hero: Candidate | None
    rows: list[FeedRow]
    hero_item: FeedItem | None
    taste_tags: tuple[str, ...]
    summary: str
    single_row: bool
