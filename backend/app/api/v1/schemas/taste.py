"""Response schema for taste search."""

from typing import Self

from pydantic import BaseModel

from app.application.ports import EntityMatch
from app.domain.models import EntityType


class EntityMatchOut(BaseModel):
    """One search match: what the caregiver taps to save a verified favourite."""

    entity_id: str
    name: str
    type: EntityType
    release_year: int | None

    @classmethod
    def from_match(cls, match: EntityMatch) -> Self:
        """Build from a taste-graph match."""
        return cls(
            entity_id=match.entity_id,
            name=match.name,
            type=match.type,
            release_year=match.release_year,
        )
