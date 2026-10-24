"""Ranking candidates: Qloo affinity first, then learned weight, then popularity. Items the
previous feed already showed sink a little within their affinity band, so a refresh feels new."""

from collections.abc import Mapping, Sequence

from app.application.agent.types import ALL_TYPES, Candidate
from app.domain.policies import rank_key


def rank(
    candidates: Sequence[Candidate],
    weights: Mapping[str, float],
    previous_refs: frozenset[str] = frozenset(),
    featured_first: bool = False,
) -> list[Candidate]:
    """The candidates best first. With `featured_first`, the agent's own picks lead."""

    def key(candidate: Candidate) -> tuple[bool, int, bool, float, float]:
        band, weight, popularity = rank_key(
            candidate.affinity, weights.get(candidate.entity_id, 0.0), candidate.popularity
        )
        featured = featured_first and candidate.featured
        return (not featured, band, candidate.entity_id in previous_refs, weight, popularity)

    return sorted(candidates, key=key)


def by_popularity(candidates: Sequence[Candidate]) -> list[Candidate]:
    """The candidates, most popular first."""
    return sorted(candidates, key=lambda candidate: -(candidate.popularity or 0.0))


def interleave(candidates: Sequence[Candidate]) -> list[Candidate]:
    """Alternate types, keeping each type's order, so a row moves between them."""
    queues = {
        entity_type: [c for c in candidates if c.entity_type is entity_type]
        for entity_type in ALL_TYPES
    }
    ordered: list[Candidate] = []
    while any(queues.values()):
        for queue in queues.values():
            if queue:
                ordered.append(queue.pop(0))
    return ordered
