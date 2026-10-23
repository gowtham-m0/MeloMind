"""Schemas for exclusions: items the caregiver rejected or hid."""

from datetime import datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, StringConstraints

from app.domain.feedback import Exclusion, ExclusionKind

ExclusionReason = Literal["rejected", "upset"]

KIND_BY_REASON: dict[str, ExclusionKind] = {
    "rejected": ExclusionKind.REJECTED,
    "upset": ExclusionKind.HIDDEN,
}


class ExclusionCreate(BaseModel):
    """Reject an item for good, or hide it (`upset`) until the caregiver reviews it."""

    entity_ref: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
    ]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    reason: ExclusionReason


class ExclusionOut(BaseModel):
    """An excluded item. `needs_review` is true for a hidden item nobody has reviewed yet."""

    id: UUID
    entity_ref: str
    title: str
    reason: ExclusionReason
    needs_review: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, exclusion: Exclusion) -> Self:
        """Build from the domain entity."""
        return cls(
            id=exclusion.id,
            entity_ref=exclusion.entity_ref,
            title=exclusion.title,
            reason="rejected" if exclusion.kind is ExclusionKind.REJECTED else "upset",
            needs_review=exclusion.needs_review,
            created_at=exclusion.created_at,
        )
