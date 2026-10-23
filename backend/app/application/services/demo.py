"""The demo seed: gives each new user the sample profiles, once."""

import logging
from collections.abc import Sequence
from uuid import UUID

from app.application.ports import ProfileRepository
from app.application.services.taste import TasteService
from app.core.errors import UpstreamError
from app.domain.models import DemoFavouriteSpec, DemoProfileSpec, Favourite, Profile

logger = logging.getLogger(__name__)


class DemoSeedService:
    """Creates the sample profiles for a user, resolving each favourite by name through search.

    The repo holds favourites by name only, so it never contains a real Qloo ID.
    """

    def __init__(
        self, profiles: ProfileRepository, taste: TasteService, specs: Sequence[DemoProfileSpec]
    ) -> None:
        self._profiles = profiles
        self._taste = taste
        self._specs = tuple(specs)

    async def seed(self, owner_id: UUID) -> list[UUID]:
        """The IDs of the user's demo profiles, creating them the first time only."""
        profiles = await self._profiles.list_for_owner(owner_id)
        demo_ids = [profile.id for profile in profiles if profile.is_demo]
        if demo_ids:
            return demo_ids
        created = [await self._create(owner_id, spec) for spec in self._specs]
        logger.info("Seeded %d demo profiles", len(created))
        return created

    async def _create(self, owner_id: UUID, spec: DemoProfileSpec) -> UUID:
        profile = Profile(
            owner_id=owner_id,
            display_name=spec.display_name,
            birth_year=spec.birth_year,
            country_code=spec.country_code,
            places_lived=list(spec.places_lived),
            languages=list(spec.languages),
            is_demo=True,
        )
        for favourite in spec.favourites:
            profile.favourites.append(await self._resolve(profile.id, favourite))
        await self._profiles.add(profile)
        return profile.id

    async def _resolve(self, profile_id: UUID, spec: DemoFavouriteSpec) -> Favourite:
        try:
            match = await self._taste.find_by_name(spec.name, spec.kind)
        except UpstreamError:
            logger.warning("Taste search failed for a demo favourite; keeping it as text")
            match = None
        return Favourite(
            profile_id=profile_id,
            name=match.name if match else spec.name,
            kind=spec.kind,
            qloo_id=match.entity_id if match else None,
            song_title=spec.song_title,
        )
