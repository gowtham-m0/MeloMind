"""`FeedbackRepository` and `ExclusionRepository` in memory."""

from copy import deepcopy
from uuid import UUID

from app.domain.feedback import Exclusion, Feedback


class InMemoryFeedbackRepository:
    """Signals in a list, in the order they arrived."""

    def __init__(self) -> None:
        self._feedback: list[Feedback] = []

    async def add(self, feedback: Feedback) -> None:
        """Store one signal."""
        self._feedback.append(deepcopy(feedback))

    async def list_for_profile(self, profile_id: UUID) -> list[Feedback]:
        """Every signal for the profile, oldest first."""
        return [deepcopy(entry) for entry in self._feedback if entry.profile_id == profile_id]


class InMemoryExclusionRepository:
    """Exclusions by ID."""

    def __init__(self) -> None:
        self._exclusions: dict[UUID, Exclusion] = {}

    async def save(self, exclusion: Exclusion) -> None:
        """Store an exclusion, replacing any with the same ID."""
        self._exclusions[exclusion.id] = deepcopy(exclusion)

    async def list_for_profile(self, profile_id: UUID) -> list[Exclusion]:
        """The profile's exclusions, oldest first."""
        owned = [entry for entry in self._exclusions.values() if entry.profile_id == profile_id]
        return [deepcopy(entry) for entry in sorted(owned, key=lambda entry: entry.created_at)]

    async def delete(self, profile_id: UUID, exclusion_id: UUID) -> bool:
        """Delete one exclusion of this profile."""
        stored = self._exclusions.get(exclusion_id)
        if stored is None or stored.profile_id != profile_id:
            return False
        del self._exclusions[exclusion_id]
        return True
