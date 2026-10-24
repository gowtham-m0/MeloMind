"""The research brief and what counts as "enough" for the feed's research pool."""

from collections import Counter
from collections.abc import Iterable

from app.application.agent.types import ALL_TYPES, Candidate, FeedContext, ResearchBrief, Tier
from app.domain.models import EntityType

# The pool should hold this many of each type, so every type row can fill from it.
PER_TYPE = 10
# Below this many of a type, the fallback tops that type up.
MIN_PER_TYPE = 6
# Nothing known yet: popular picks.
COLD_POPULARITY = 0.7


def cold_start_tier(context: FeedContext) -> Tier:
    """A: 3 or more signals. B: 1–2. C: nothing specific yet."""
    count = len(context.signals)
    if count >= 3:
        return "A"
    if count:
        return "B"
    return "C"


def build_brief(context: FeedContext) -> ResearchBrief:
    """The goal and constraints for the research agent."""
    tier = cold_start_tier(context)
    return ResearchBrief(
        goal=(
            f"A varied home feed for {context.first_name} across music, films, TV and books: "
            "things they'll probably love, plus a few fresh surprises."
        ),
        tier=tier,
        per_type=PER_TYPE,
        country_code=context.country_code,
        popularity_min=COLD_POPULARITY if tier == "C" else None,
        signals=context.signals,
        tag_hints=context.previous_tags[:3] if tier != "A" else (),
    )


def shortfall(candidates: Iterable[Candidate]) -> set[EntityType]:
    """Types with fewer than `MIN_PER_TYPE` candidates."""
    counts = Counter(candidate.entity_type for candidate in candidates)
    return {entity_type for entity_type in ALL_TYPES if counts[entity_type] < MIN_PER_TYPE}


def has_enough(candidates: Iterable[Candidate]) -> bool:
    """True when every type has enough candidates for its row."""
    return not shortfall(candidates)
