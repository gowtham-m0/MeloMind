"""Favourite routes, nested under the profile they belong to."""

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep, ProfileServiceDep
from app.api.v1.schemas.profiles import FavouriteCreate, FavouriteOut

router = APIRouter(prefix="/profiles/{profile_id}/favourites", tags=["favourites"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_favourite(
    profile_id: UUID, body: FavouriteCreate, user: CurrentUserDep, profiles: ProfileServiceDep
) -> FavouriteOut:
    """Save a favourite. It's verified when `entity_id` comes from a taste-search match."""
    favourite = await profiles.add_favourite(
        user.id, profile_id, body.name, body.kind, body.entity_id, body.song_title, body.image_url
    )
    return FavouriteOut.from_domain(favourite)


@router.delete("/{favourite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favourite(
    profile_id: UUID, favourite_id: UUID, user: CurrentUserDep, profiles: ProfileServiceDep
) -> None:
    """Delete one favourite."""
    await profiles.remove_favourite(user.id, profile_id, favourite_id)
