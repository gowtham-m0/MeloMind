"""Use cases for exclusions: the "not interested" list, with undo."""

from uuid import UUID

from app.application.ports import ExclusionRepository
from app.application.services.feed import FeedService
from app.application.services.profiles import ProfileService
from app.core.errors import NotFoundError
from app.domain.feedback import Exclusion


class ExclusionService:
    """The not-interested list, for its owner."""

    def __init__(
        self, profiles: ProfileService, exclusions: ExclusionRepository, feeds: FeedService
    ) -> None:
        self._profiles = profiles
        self._exclusions = exclusions
        self._feeds = feeds

    async def list_for_profile(self, owner_id: UUID, profile_id: UUID) -> list[Exclusion]:
        """The profile's exclusions, newest first."""
        await self._profiles.get(owner_id, profile_id)
        entries = await self._exclusions.list_for_profile(profile_id)
        return sorted(entries, key=lambda entry: entry.created_at, reverse=True)

    async def remove(self, owner_id: UUID, profile_id: UUID, exclusion_id: UUID) -> list[Exclusion]:
        """Undo a "not interested". Returns the remaining exclusions, newest first."""
        await self._profiles.get(owner_id, profile_id)
        if not await self._exclusions.delete(profile_id, exclusion_id):
            raise NotFoundError("Exclusion not found.")
        await self._feeds.mark_stale(profile_id)
        return await self.list_for_profile(owner_id, profile_id)
