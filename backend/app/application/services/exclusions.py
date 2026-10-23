"""Use cases for exclusions: what the caregiver rejected (never again) or hid (until reviewed)."""

from uuid import UUID

from app.application.ports import ExclusionRepository, SessionRepository
from app.application.services.profiles import ProfileService
from app.core.errors import ConflictError, InvalidInputError, NotFoundError
from app.domain.feedback import Blocklist, Exclusion, ExclusionKind
from app.domain.models import utc_now
from app.domain.sessions import SessionStatus

REF_MAX = 120
TITLE_MAX = 200


class ExclusionService:
    """Exclusions for their owner. Only the caregiver can hide or reject an item (rule 7)."""

    def __init__(
        self,
        profiles: ProfileService,
        exclusions: ExclusionRepository,
        sessions: SessionRepository,
    ) -> None:
        self._profiles = profiles
        self._exclusions = exclusions
        self._sessions = sessions

    async def list_for_profile(self, owner_id: UUID, profile_id: UUID) -> list[Exclusion]:
        """The profile's exclusions, oldest first."""
        await self._profiles.get(owner_id, profile_id)
        return await self._exclusions.list_for_profile(profile_id)

    async def add(
        self, owner_id: UUID, profile_id: UUID, entity_ref: str, title: str, kind: ExclusionKind
    ) -> list[Exclusion]:
        """Reject or hide an item by its ref. Returns every exclusion."""
        await self._profiles.get(owner_id, profile_id)
        await self.block(profile_id, _clean(entity_ref, REF_MAX), _clean(title, TITLE_MAX), kind)
        return await self._exclusions.list_for_profile(profile_id)

    async def remove(self, owner_id: UUID, profile_id: UUID, exclusion_id: UUID) -> list[Exclusion]:
        """Let a hidden item back in, after review. A rejection is for good (rule 6). Returns the
        remaining exclusions."""
        await self._profiles.get(owner_id, profile_id)
        existing = next(
            (
                entry
                for entry in await self._exclusions.list_for_profile(profile_id)
                if entry.id == exclusion_id
            ),
            None,
        )
        if existing is None:
            raise NotFoundError("Exclusion not found.")
        if existing.kind is ExclusionKind.REJECTED:
            raise ConflictError("A rejected item stays rejected.")
        await self._exclusions.delete(profile_id, exclusion_id)
        return await self._exclusions.list_for_profile(profile_id)

    async def block(
        self, profile_id: UUID, entity_ref: str, title: str, kind: ExclusionKind
    ) -> Exclusion:
        """Record an exclusion for a profile the caller has already checked, and take the item out
        of drafts waiting for review. One per ref: a rejection stays a rejection, and a hidden
        item can become a rejection."""
        await self._remove_from_drafts(profile_id, entity_ref, title)
        existing = next(
            (
                entry
                for entry in await self._exclusions.list_for_profile(profile_id)
                if entry.entity_ref == entity_ref
            ),
            None,
        )
        if existing is not None:
            if existing.kind is ExclusionKind.REJECTED or existing.kind is kind:
                return existing
            existing.kind = kind
            existing.needs_review = False
            await self._exclusions.save(existing)
            return existing
        exclusion = Exclusion(
            profile_id=profile_id,
            entity_ref=entity_ref,
            title=title,
            kind=kind,
            needs_review=kind is ExclusionKind.HIDDEN,
        )
        await self._exclusions.save(exclusion)
        return exclusion

    async def _remove_from_drafts(self, profile_id: UUID, entity_ref: str, title: str) -> None:
        """A blocked item never appears again (rule 6), so drafts lose it too. Sessions already
        approved keep their record; the shelf and the warm-up leave the item out instead."""
        blocklist = Blocklist.from_exclusions(
            [Exclusion(profile_id, entity_ref, title, ExclusionKind.REJECTED)]
        )
        drafts = await self._sessions.list_for_profile(profile_id, frozenset({SessionStatus.DRAFT}))
        for draft in drafts:
            kept = [item for item in draft.items if not blocklist.blocks(item.ref, item.title)]
            if len(kept) == len(draft.items):
                continue
            draft.items = kept
            draft.renumber()
            draft.updated_at = utc_now()
            await self._sessions.update(draft)


def _clean(value: str, max_length: int) -> str:
    text = " ".join(value.split())
    if not text or len(text) > max_length:
        raise InvalidInputError(f"Give a value of 1 to {max_length} characters.")
    return text
