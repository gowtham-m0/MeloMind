"""The Person-mode shelf: only what the caregiver approved, and only what can play.

It holds verified favourites with a playable video, items from approved sessions, and the
latest approved warm-up set. Excluded and hidden items never appear (rules 3, 6 and 7).
"""

import logging
from uuid import UUID

from app.application.ports import ExclusionRepository, MediaResolver, SessionRepository
from app.application.services.profiles import ProfileService
from app.core.errors import UpstreamError
from app.domain.feedback import Blocklist
from app.domain.media import media_query
from app.domain.models import Favourite, Profile, search_type_for
from app.domain.policies import era_middle_year
from app.domain.sessions import (
    APPROVED_STATUSES,
    MediaRef,
    ShelfItem,
    ShelfOrigin,
    favourite_ref,
)

logger = logging.getLogger(__name__)


class ShelfService:
    """Builds the shelf for a profile, in code, every time it's asked for."""

    def __init__(
        self,
        profiles: ProfileService,
        sessions: SessionRepository,
        exclusions: ExclusionRepository,
        media: MediaResolver,
    ) -> None:
        self._profiles = profiles
        self._sessions = sessions
        self._exclusions = exclusions
        self._media = media

    async def items(self, owner_id: UUID, profile_id: UUID) -> list[ShelfItem]:
        """The shelf of a profile the user owns."""
        return await self.items_for(await self._profiles.get(owner_id, profile_id))

    async def items_for(self, profile: Profile) -> list[ShelfItem]:
        """Favourites first, then the warm-up set, then approved sessions, newest first."""
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        shelf: dict[str, ShelfItem] = {}
        for favourite in profile.favourites:
            card = await self._favourite_card(profile, favourite)
            if card is not None:
                shelf.setdefault(card.ref, card)
        approved = await self._sessions.list_for_profile(profile.id, APPROVED_STATUSES)
        warmup = next((session for session in approved if session.is_warmup), None)
        if warmup is not None:
            for item in warmup.items:
                card = ShelfItem.from_item(item, ShelfOrigin.WARMUP)
                if card is not None:
                    shelf.setdefault(card.ref, card)
        for session in approved:
            if session.is_warmup:
                continue
            for item in session.items:
                card = ShelfItem.from_item(item, ShelfOrigin.SESSION)
                if card is not None:
                    shelf.setdefault(card.ref, card)
        return [card for card in shelf.values() if not blocklist.blocks(card.ref, card.title)]

    async def _favourite_card(self, profile: Profile, favourite: Favourite) -> ShelfItem | None:
        """A card for a verified favourite that has a playable video. Books have none."""
        if not favourite.verified:
            return None
        query = media_query(
            favourite.name,
            search_type_for(favourite.kind),
            None,
            era_middle_year(profile.birth_year),
            song_title=favourite.song_title,
        )
        if query is None:
            return None
        try:
            media = await self._media.resolve(query)
        except UpstreamError:
            logger.warning("No media for a favourite this time: the video service failed")
            return None
        if media is None:
            return None
        return ShelfItem(
            ref=favourite_ref(favourite),
            title=favourite.song_title or favourite.name,
            kind=favourite.kind,
            release_year=None,
            media=MediaRef(
                provider=media.provider,
                ref=media.video_id,
                duration_s=media.duration_s,
                title=media.title,
            ),
            origin=ShelfOrigin.FAVOURITE,
        )
