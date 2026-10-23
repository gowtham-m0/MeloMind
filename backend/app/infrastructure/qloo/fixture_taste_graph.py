"""`TasteGraph` over the hand-written demo fixtures, used when `QLOO_API_KEY` is empty."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.ports import EntityMatch, InsightsQuery, TasteSource
from app.domain.models import EntityType
from app.domain.names import normalise_name
from app.infrastructure.qloo.urns import COUNTRY_FILTER_TYPES, TYPE_BY_URN, YEAR_FILTER_TYPES

FIXTURES_DIR = Path(__file__).parent / "fixtures"
# Affinity for an entity that only shares a tag with the signals, below any hand-written affinity.
TAG_AFFINITY = 0.5
# Affinity for an entity in the scored set that nothing in the signals relates to.
UNRELATED_AFFINITY = 0.1


@dataclass(frozen=True)
class _Entity:
    entity_id: str
    name: str
    names: frozenset[str]
    type: EntityType
    release_year: int
    country: str
    popularity: float
    tags: frozenset[str]

    def to_match(self, affinity: float | None = None) -> EntityMatch:
        return EntityMatch(
            entity_id=self.entity_id,
            name=self.name,
            type=self.type,
            source="demo_fixture",
            release_year=self.release_year,
            popularity=self.popularity,
            affinity=affinity,
        )


def _read(fixtures_dir: Path, name: str) -> dict[str, Any]:
    return json.loads((fixtures_dir / name).read_text(encoding="utf-8"))


def _parse_entity(raw: dict[str, Any]) -> _Entity:
    names = [raw["name"], *raw.get("aliases", [])]
    return _Entity(
        entity_id=raw["entity_id"],
        name=raw["name"],
        names=frozenset(normalise_name(name) for name in names),
        type=TYPE_BY_URN[raw["type"]],
        release_year=raw["release_year"],
        country=raw["country"],
        popularity=raw["popularity"],
        tags=frozenset(raw["tags"]),
    )


class FixtureTasteGraph:
    """Search and insights over `fixtures/`, applying the same filters as live Qloo."""

    def __init__(self, fixtures_dir: Path = FIXTURES_DIR) -> None:
        entities = [_parse_entity(raw) for raw in _read(fixtures_dir, "entities.json")["entities"]]
        self._entities = {entity.entity_id: entity for entity in entities}
        self._related: dict[str, dict[str, float]] = {
            signal: {item["entity_id"]: item["affinity"] for item in items}
            for signal, items in _read(fixtures_dir, "insights.json")["related"].items()
        }

    @property
    def source(self) -> TasteSource:
        """Fixture results are always demo data."""
        return "demo_fixture"

    async def search(
        self, query: str, types: tuple[EntityType, ...] = (), take: int = 5
    ) -> list[EntityMatch]:
        """Entities whose name or alias contains the query. Exact matches first, then popularity."""
        needle = normalise_name(query)
        if not needle:
            return []
        hits = [
            entity
            for entity in self._entities.values()
            if (not types or entity.type in types) and any(needle in name for name in entity.names)
        ]
        hits.sort(key=lambda entity: (needle not in entity.names, -entity.popularity))
        return [entity.to_match() for entity in hits[:take]]

    async def insights(self, query: InsightsQuery) -> list[EntityMatch]:
        """Related entities of one type, scored by the signals, filtered like `/v2/insights`."""
        scores = self._score(query)
        candidates = [
            self._entities[entity_id]
            for entity_id in self._candidate_ids(query, scores)
            if entity_id in self._entities
        ]
        kept = [entity for entity in candidates if self._passes_filters(entity, query)]
        kept.sort(key=lambda entity: (-scores.get(entity.entity_id, 0.0), -entity.popularity))
        has_signals = bool(query.signal_entities or query.signal_tags)
        return [
            entity.to_match(scores.get(entity.entity_id) if has_signals else None)
            for entity in kept[: query.take]
        ]

    def _score(self, query: InsightsQuery) -> dict[str, float]:
        scores: dict[str, float] = {}
        for signal in query.signal_entities:
            for entity_id, affinity in self._related.get(signal, {}).items():
                scores[entity_id] = max(scores.get(entity_id, 0.0), affinity)
        tags = set(query.signal_tags)
        if tags:
            for entity in self._entities.values():
                if entity.tags & tags:
                    scores[entity.entity_id] = max(scores.get(entity.entity_id, 0.0), TAG_AFFINITY)
        for signal in query.signal_entities:
            scores.pop(signal, None)
        if query.signal_entities or query.signal_tags:
            for entity_id in query.score_entities:
                scores.setdefault(entity_id, UNRELATED_AFFINITY)
        return scores

    def _candidate_ids(self, query: InsightsQuery, scores: dict[str, float]) -> list[str]:
        if query.score_entities:
            return list(query.score_entities)
        if query.signal_entities or query.signal_tags:
            return list(scores)
        return list(self._entities)

    @staticmethod
    def _passes_filters(entity: _Entity, query: InsightsQuery) -> bool:
        if entity.type is not query.entity_type:
            return False
        if entity.entity_id in query.exclude_entities or entity.tags & set(query.exclude_tags):
            return False
        if query.popularity_min is not None and entity.popularity < query.popularity_min:
            return False
        if entity.type in YEAR_FILTER_TYPES:
            if query.year_min is not None and entity.release_year < query.year_min:
                return False
            if query.year_max is not None and entity.release_year > query.year_max:
                return False
        return not (
            entity.type in COUNTRY_FILTER_TYPES
            and query.country_code is not None
            and entity.country != query.country_code.upper()
        )
