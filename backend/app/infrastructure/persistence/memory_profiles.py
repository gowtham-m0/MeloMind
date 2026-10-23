"""`ProfileRepository` in memory: for tests, and for local runs without `DATABASE_URL`."""

from copy import deepcopy
from uuid import UUID

from app.domain.models import Favourite, Profile


class InMemoryProfileRepository:
    """Keeps copies of profiles in a dict, so callers can't change stored data by accident."""

    def __init__(self) -> None:
        self._profiles: dict[UUID, Profile] = {}

    async def list_for_owner(self, owner_id: UUID) -> list[Profile]:
        """Every profile the user owns, oldest first."""
        owned = [profile for profile in self._profiles.values() if profile.owner_id == owner_id]
        return [deepcopy(profile) for profile in sorted(owned, key=lambda p: p.created_at)]

    async def get(self, profile_id: UUID) -> Profile | None:
        """One profile with its favourites."""
        profile = self._profiles.get(profile_id)
        return deepcopy(profile) if profile else None

    async def add(self, profile: Profile) -> None:
        """Store a new profile and its favourites."""
        self._profiles[profile.id] = deepcopy(profile)

    async def update(self, profile: Profile) -> None:
        """Save the profile's own fields, keeping the stored favourites."""
        stored = self._profiles.get(profile.id)
        if stored is None:
            return
        updated = deepcopy(profile)
        updated.favourites = stored.favourites
        self._profiles[profile.id] = updated

    async def delete(self, profile_id: UUID) -> None:
        """Delete the profile; its favourites go with it."""
        self._profiles.pop(profile_id, None)

    async def add_favourite(self, favourite: Favourite) -> None:
        """Store a new favourite on its profile."""
        stored = self._profiles.get(favourite.profile_id)
        if stored is not None:
            stored.favourites.append(deepcopy(favourite))

    async def delete_favourite(self, profile_id: UUID, favourite_id: UUID) -> bool:
        """Delete one favourite. False when the profile has no such favourite."""
        stored = self._profiles.get(profile_id)
        if stored is None:
            return False
        kept = [favourite for favourite in stored.favourites if favourite.id != favourite_id]
        removed = len(kept) != len(stored.favourites)
        stored.favourites = kept
        return removed
