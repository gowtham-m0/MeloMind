"""Use cases for one item: its details, "More like this", and the optional YouTube preview."""

import logging
from dataclasses import dataclass
from uuid import UUID

from app.application.agent.cards import candidate_from_match, to_card
from app.application.ports import (
    CatalogRepository,
    ExclusionRepository,
    FeedRepository,
    InsightsQuery,
    MediaResolver,
    PlayableMedia,
    TasteGraph,
)
from app.application.services.profiles import ProfileService
from app.core.errors import NotFoundError, UpstreamError
from app.domain.feed import FeedItem, is_favourite_ref
from app.domain.feedback import Blocklist
from app.domain.models import EntityType

logger = logging.getLogger(__name__)

MORE_LIKE_THIS = 12
# Ask for a few more, so excluded items and the item itself can drop out.
MORE_LIKE_THIS_TAKE = 16


@dataclass(frozen=True)
class ItemDetail:
    """An item with what the detail sheet shows besides the card."""

    item: FeedItem
    more_like_this: list[FeedItem]
    preview_available: bool


class ItemService:
    """Item details for their owner's profiles. Excluded items are not found (rule 3)."""

    def __init__(
        self,
        profiles: ProfileService,
        feeds: FeedRepository,
        catalog: CatalogRepository,
        exclusions: ExclusionRepository,
        taste: TasteGraph,
        media: MediaResolver | None = None,
    ) -> None:
        self._profiles = profiles
        self._feeds = feeds
        self._catalog = catalog
        self._exclusions = exclusions
        self._taste = taste
        self._media = media

    async def detail(self, owner_id: UUID, profile_id: UUID, ref: str) -> ItemDetail:
        """The item, and more like it."""
        profile = await self._profiles.get(owner_id, profile_id)
        blocklist = Blocklist.from_exclusions(await self._exclusions.list_for_profile(profile.id))
        item = await self._find(profile.id, ref)
        if item is None or blocklist.blocks(item.ref, item.title):
            raise NotFoundError("Item not found.")
        more = await self._more_like_this(item, blocklist, profile.country_code)
        return ItemDetail(
            item=item,
            more_like_this=more,
            preview_available=self._media is not None and item.entity_type is not EntityType.BOOK,
        )

    async def preview(self, owner_id: UUID, profile_id: UUID, ref: str) -> PlayableMedia:
        """A YouTube video for the item, looked up only now (rule 6). Not found when there's
        no playable one: the button hides, never an unrelated video."""
        profile = await self._profiles.get(owner_id, profile_id)
        item = await self._find(profile.id, ref)
        if self._media is None or item is None or item.entity_type is EntityType.BOOK:
            raise NotFoundError("No preview for this item.")
        try:
            media = await self._media.resolve(preview_query(item))
        except UpstreamError:
            logger.warning("Preview lookup failed")
            raise NotFoundError("No preview right now.") from None
        if media is None:
            raise NotFoundError("No playable preview found.")
        return media

    async def _find(self, profile_id: UUID, ref: str) -> FeedItem | None:
        feed = await self._feeds.latest(profile_id, done_only=True)
        item = feed.find(ref) if feed else None
        if item is not None:
            return item
        return (await self._catalog.get_many([ref])).get(ref)

    async def _more_like_this(
        self, item: FeedItem, blocklist: Blocklist, country_code: str | None
    ) -> list[FeedItem]:
        if is_favourite_ref(item.ref):
            return []
        query = InsightsQuery(
            entity_type=item.entity_type,
            take=MORE_LIKE_THIS_TAKE,
            signal_entities=(item.ref,),
            exclude_entities=blocklist.qloo_ids,
        )
        try:
            matches = await self._taste.insights(query)
        except UpstreamError:
            logger.warning("More like this: Qloo failed")
            return []
        cards = [
            to_card(
                candidate_from_match(match, f"similar to {item.title}", item.ref, item.title),
                country_code,
            )
            for match in matches
            if match.entity_id != item.ref and not blocklist.blocks(match.entity_id, match.name)
        ][:MORE_LIKE_THIS]
        await self._catalog.put_many(cards)
        return cards


def preview_query(item: FeedItem) -> str:
    """What to search on YouTube: an artist's music video, or a film's or show's trailer."""
    if item.entity_type is EntityType.ARTIST:
        return f"{item.title} official music video"
    year = f" {item.year}" if item.year else ""
    return f"{item.title}{year} official trailer"
