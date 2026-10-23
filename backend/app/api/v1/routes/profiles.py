"""Profile routes. Every route is scoped to the signed-in owner; others' profiles are 404."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, ProfileServiceDep
from app.api.v1.schemas.profiles import ProfileCreate, ProfileOut, ProfileUpdate

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("")
async def list_profiles(user: CurrentUserDep, profiles: ProfileServiceDep) -> list[ProfileOut]:
    """The signed-in user's profiles, oldest first."""
    return [ProfileOut.from_domain(profile) for profile in await profiles.list(user.id)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate, user: CurrentUserDep, profiles: ProfileServiceDep
) -> ProfileOut:
    """Create a profile from a display name and birth year, plus anything else known."""
    profile = await profiles.create(
        user.id, body.display_name, body.birth_year, body.optional_fields()
    )
    return ProfileOut.from_domain(profile)


@router.get("/{profile_id}")
async def get_profile(
    profile_id: UUID, user: CurrentUserDep, profiles: ProfileServiceDep
) -> ProfileOut:
    """One profile with its favourites."""
    return ProfileOut.from_domain(await profiles.get(user.id, profile_id))


@router.patch("/{profile_id}")
async def update_profile(
    profile_id: UUID, body: ProfileUpdate, user: CurrentUserDep, profiles: ProfileServiceDep
) -> ProfileOut:
    """Change some of a profile's fields."""
    return ProfileOut.from_domain(await profiles.update(user.id, profile_id, body.changes()))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    profile_id: UUID, user: CurrentUserDep, profiles: ProfileServiceDep
) -> None:
    """Delete a profile and everything that belongs to it."""
    await profiles.delete(user.id, profile_id)
