"""The library: what the user liked and saved, newest first."""

from dataclasses import dataclass
from uuid import UUID

from app.application.ports import CatalogRepository, FeedbackRepository
from app.application.services.profiles import ProfileService
from app.domain.feed import FeedItem, ItemSource, is_favourite_ref
from app.domain.feedback import Feedback, Signal
from app.domain.links import platform_links
from app.domain.models import EntityType
from app.domain.policies import item_states


@dataclass(frozen=True)
class Library:
    """Liked and saved items, newest first."""

    liked: list[FeedItem]
    saved: list[FeedItem]


class LibraryService:
    """The library for its owner's profiles."""

    def __init__(
        self,
        profiles: ProfileService,
        feedback: FeedbackRepository,
        catalog: CatalogRepository,
        source: ItemSource,
    ) -> None:
        self._profiles = profiles
        self._feedback = feedback
        self._catalog = catalog
        self._source = source

    async def library(self, owner_id: UUID, profile_id: UUID) -> Library:
        """Liked and saved items, each as a card."""
        profile = await self._profiles.get(owner_id, profile_id)
        feedback = await self._feedback.list_for_profile(profile.id)
        states = item_states(feedback)
        latest: dict[str, Feedback] = {}
        for entry in feedback:
            latest[entry.item_ref] = entry
        order = sorted(states, key=lambda ref: latest[ref].created_at, reverse=True)
        known = await self._catalog.get_many(order)
        cards = {
            ref: known.get(ref) or _fallback_card(latest[ref], profile.country_code, self._source)
            for ref in order
        }
        return Library(
            liked=[cards[ref] for ref in order if Signal.LIKED in states[ref]],
            saved=[cards[ref] for ref in order if Signal.SAVED in states[ref]],
        )


def _fallback_card(entry: Feedback, country_code: str | None, source: ItemSource) -> FeedItem:
    """A plain card when the catalog doesn't hold the item."""
    entity_type = entry.entity_type or EntityType.ARTIST
    return FeedItem(
        ref=entry.item_ref,
        title=entry.title,
        entity_type=entity_type,
        source=ItemSource.FAVOURITE if is_favourite_ref(entry.item_ref) else source,
        reason="From your library.",
        links=platform_links(entry.title, entity_type, country_code=country_code),
    )
