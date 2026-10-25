"""The demo seed: gives each new user the sample profiles, once, each with a few likes and one
"not interested" item, and its first feed being built in the background so it's ready when they
open it."""

import logging
from collections.abc import Sequence
from datetime import datetime, timedelta
from uuid import UUID

from app.application.ports import (
    EntityMatch,
    ExclusionRepository,
    FeedbackRepository,
    JournalRepository,
    ProfileRepository,
)
from app.application.services.feed import FeedService
from app.application.services.taste import TasteService
from app.core.errors import UpstreamError
from app.domain.feedback import Exclusion, Feedback, Signal
from app.domain.journal import (
    JournalLink,
    JournalNode,
    LinkSource,
    LinkStatus,
    NodeKind,
    signal_type,
)
from app.domain.models import (
    DemoFavouriteSpec,
    DemoJournalSpec,
    DemoProfileSpec,
    Favourite,
    FavouriteKind,
    Profile,
    utc_now,
)

logger = logging.getLogger(__name__)


class DemoSeedService:
    """Creates the sample profiles for a user, resolving each favourite by name through search.

    The repo holds favourites, likes and exclusions by name only, so it never contains a real
    Qloo ID. A like or exclusion that search can't find is skipped: there's nothing to steer by.
    """

    def __init__(
        self,
        profiles: ProfileRepository,
        taste: TasteService,
        specs: Sequence[DemoProfileSpec],
        feedback: FeedbackRepository,
        exclusions: ExclusionRepository,
        feeds: FeedService | None = None,
        journal: JournalRepository | None = None,
    ) -> None:
        self._profiles = profiles
        self._taste = taste
        self._specs = tuple(specs)
        self._feedback = feedback
        self._exclusions = exclusions
        self._feeds = feeds
        self._journal = journal

    async def seed(self, owner_id: UUID) -> list[UUID]:
        """The IDs of the user's demo profiles, creating them the first time only."""
        profiles = await self._profiles.list_for_owner(owner_id)
        demo_ids = [profile.id for profile in profiles if profile.is_demo]
        if demo_ids:
            return demo_ids
        created = [await self._create(owner_id, spec) for spec in self._specs]
        logger.info("Seeded %d demo profiles", len(created))
        if self._feeds is not None:
            for profile_id in created:
                await self._feeds.refresh(owner_id, profile_id, count_towards_limit=False)
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
        await self._add_signals(profile.id, spec)
        for entry in spec.journal:
            await self._add_entry(profile.id, entry)
        return profile.id

    async def _add_entry(self, profile_id: UUID, spec: DemoJournalSpec) -> None:
        """A sample entry with its links already confirmed, as if the user had said yes. Each
        confirmed item Qloo knows gets its `journal_confirmed` signal, once."""
        if self._journal is None:
            return
        now = utc_now()
        day = (now - timedelta(days=spec.days_ago)).date()
        entry = JournalNode(
            profile_id=profile_id,
            kind=NodeKind.ENTRY,
            title=day.isoformat(),
            body=spec.text,
            date=day,
            mood=spec.mood,
            created_at=now - timedelta(days=spec.days_ago),
        )
        await self._journal.add_node(entry)
        existing = await self._journal.list_nodes(profile_id)
        for link in spec.links:
            kind = NodeKind(link.kind)
            node = next((n for n in existing if n.same_item(kind, link.name, None)), None)
            if node is None:
                node = await self._demo_node(profile_id, kind, link.name)
                if node is None:
                    continue
                await self._journal.add_node(node)
                existing.append(node)
                await self._confirm_signal(profile_id, node, entry.created_at)
            await self._journal.add_link(
                JournalLink(
                    profile_id=profile_id,
                    from_id=entry.id,
                    to_id=node.id,
                    source=LinkSource.AGENT,
                    status=LinkStatus.CONFIRMED,
                    reason="You mentioned it.",
                    created_at=entry.created_at,
                )
            )

    async def _demo_node(self, profile_id: UUID, kind: NodeKind, name: str) -> JournalNode | None:
        if kind is NodeKind.PLACE:
            return JournalNode(profile_id=profile_id, kind=kind, title=name)
        match = await self._find(DemoFavouriteSpec(name=name, kind=FavouriteKind(kind.value)))
        if match is None:
            return None
        return JournalNode(
            profile_id=profile_id,
            kind=kind,
            title=match.name,
            year=match.release_year,
            qloo_id=match.entity_id,
            image_url=match.image_url,
        )

    async def _confirm_signal(self, profile_id: UUID, node: JournalNode, at: datetime) -> None:
        """The signal is dated with its entry, so the sample likes stay the newest taste."""
        entity_type = signal_type(node.kind)
        if node.qloo_id is None or entity_type is None:
            return
        await self._feedback.add(
            Feedback(
                profile_id,
                node.qloo_id,
                node.title,
                Signal.JOURNAL_CONFIRMED,
                entity_type,
                created_at=at,
            )
        )

    async def _add_signals(self, profile_id: UUID, spec: DemoProfileSpec) -> None:
        for item in spec.likes:
            if match := await self._find(item):
                await self._feedback.add(
                    Feedback(profile_id, match.entity_id, match.name, Signal.LIKED, match.type)
                )
        for item in spec.not_interested:
            if match := await self._find(item):
                await self._feedback.add(
                    Feedback(
                        profile_id, match.entity_id, match.name, Signal.NOT_INTERESTED, match.type
                    )
                )
                await self._exclusions.save(
                    Exclusion(profile_id, match.entity_id, match.name, match.type)
                )

    async def _find(self, spec: DemoFavouriteSpec) -> EntityMatch | None:
        try:
            return await self._taste.find_by_name(spec.name, spec.kind)
        except UpstreamError:
            logger.warning("Taste search failed for a demo item")
            return None

    async def _resolve(self, profile_id: UUID, spec: DemoFavouriteSpec) -> Favourite:
        match = await self._find(spec)
        return Favourite(
            profile_id=profile_id,
            name=match.name if match else spec.name,
            kind=spec.kind,
            qloo_id=match.entity_id if match else None,
            song_title=spec.song_title,
            image_url=match.image_url if match else None,
        )
