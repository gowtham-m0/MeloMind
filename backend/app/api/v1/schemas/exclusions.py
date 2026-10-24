"""Schemas for exclusions: the items marked "not interested"."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from app.domain.feedback import Exclusion
from app.domain.models import EntityType


class ExclusionOut(BaseModel):
    """An item the user is not interested in. Deleting it undoes that."""

    id: UUID
    entity_ref: str
    title: str
    entity_type: EntityType | None
    created_at: datetime

    @classmethod
    def from_domain(cls, exclusion: Exclusion) -> Self:
        """Build from the domain entity."""
        return cls(
            id=exclusion.id,
            entity_ref=exclusion.entity_ref,
            title=exclusion.title,
            entity_type=exclusion.entity_type,
            created_at=exclusion.created_at,
        )
