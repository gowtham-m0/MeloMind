"""Exclusion routes: list, add and remove the items a caregiver rejected or hid."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, ExclusionServiceDep
from app.api.v1.schemas.exclusions import KIND_BY_REASON, ExclusionCreate, ExclusionOut

router = APIRouter(prefix="/profiles/{profile_id}/exclusions", tags=["exclusions"])


@router.get("")
async def list_exclusions(
    profile_id: UUID, user: CurrentUserDep, exclusions: ExclusionServiceDep
) -> list[ExclusionOut]:
    """The profile's exclusions, oldest first."""
    return [
        ExclusionOut.from_domain(entry)
        for entry in await exclusions.list_for_profile(user.id, profile_id)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_exclusion(
    profile_id: UUID, body: ExclusionCreate, user: CurrentUserDep, exclusions: ExclusionServiceDep
) -> list[ExclusionOut]:
    """Reject or hide an item. Returns every exclusion."""
    entries = await exclusions.add(
        user.id, profile_id, body.entity_ref, body.title, KIND_BY_REASON[body.reason]
    )
    return [ExclusionOut.from_domain(entry) for entry in entries]


@router.delete("/{exclusion_id}")
async def remove_exclusion(
    profile_id: UUID, exclusion_id: UUID, user: CurrentUserDep, exclusions: ExclusionServiceDep
) -> list[ExclusionOut]:
    """Let an item back in after review. Returns the remaining exclusions."""
    entries = await exclusions.remove(user.id, profile_id, exclusion_id)
    return [ExclusionOut.from_domain(entry) for entry in entries]
