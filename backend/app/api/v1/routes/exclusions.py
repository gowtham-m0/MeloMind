"""Exclusion routes: the "not interested" list, with undo."""

from uuid import UUID

from fastapi import APIRouter

from app.api.deps import CurrentUserDep, ExclusionServiceDep
from app.api.v1.schemas.exclusions import ExclusionOut

router = APIRouter(prefix="/profiles/{profile_id}/exclusions", tags=["exclusions"])


@router.get("")
async def list_exclusions(
    profile_id: UUID, user: CurrentUserDep, exclusions: ExclusionServiceDep
) -> list[ExclusionOut]:
    """The items marked "not interested", newest first."""
    return [
        ExclusionOut.from_domain(entry)
        for entry in await exclusions.list_for_profile(user.id, profile_id)
    ]


@router.delete("/{exclusion_id}")
async def remove_exclusion(
    profile_id: UUID, exclusion_id: UUID, user: CurrentUserDep, exclusions: ExclusionServiceDep
) -> list[ExclusionOut]:
    """Undo a "not interested". Returns the remaining exclusions and marks the feed stale."""
    entries = await exclusions.remove(user.id, profile_id, exclusion_id)
    return [ExclusionOut.from_domain(entry) for entry in entries]
