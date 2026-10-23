"""`FeedbackRepository` and `ExclusionRepository` on Postgres."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.feedback import Actor, Exclusion, ExclusionKind, Feedback
from app.domain.models import EntityType
from app.infrastructure.persistence.models import ExclusionRow, FeedbackRow


def _feedback_to_domain(row: FeedbackRow) -> Feedback:
    return Feedback(
        id=row.id,
        profile_id=row.profile_id,
        session_id=row.session_id,
        item_ref=row.item_ref,
        title=row.title,
        entity_type=EntityType(row.entity_type) if row.entity_type else None,
        actor=Actor(row.actor),
        kind=row.kind,
        note=row.note,
        played_s=row.played_s,
        created_at=row.created_at,
    )


def _exclusion_to_domain(row: ExclusionRow) -> Exclusion:
    return Exclusion(
        id=row.id,
        profile_id=row.profile_id,
        entity_ref=row.entity_ref,
        title=row.title,
        kind=ExclusionKind(row.kind),
        needs_review=row.needs_review,
        created_at=row.created_at,
    )


class PostgresFeedbackRepository:
    """Reactions and signals in Postgres."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def add(self, feedback: Feedback) -> None:
        """Store one reaction or signal."""
        async with self._sessions() as db, db.begin():
            db.add(
                FeedbackRow(
                    id=feedback.id,
                    profile_id=feedback.profile_id,
                    session_id=feedback.session_id,
                    item_ref=feedback.item_ref,
                    title=feedback.title,
                    entity_type=feedback.entity_type.value if feedback.entity_type else None,
                    actor=feedback.actor.value,
                    kind=feedback.kind,
                    note=feedback.note,
                    played_s=feedback.played_s,
                    created_at=feedback.created_at,
                )
            )

    async def list_for_profile(self, profile_id: UUID) -> list[Feedback]:
        """Every reaction and signal for the profile, oldest first."""
        async with self._sessions() as db:
            rows = await db.scalars(
                select(FeedbackRow)
                .where(FeedbackRow.profile_id == profile_id)
                .order_by(FeedbackRow.created_at)
            )
            return [_feedback_to_domain(row) for row in rows]


class PostgresExclusionRepository:
    """Exclusions in Postgres, one per item ref per profile."""

    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, exclusion: Exclusion) -> None:
        """Insert the exclusion, or update the one with the same ID."""
        async with self._sessions() as db, db.begin():
            await db.merge(
                ExclusionRow(
                    id=exclusion.id,
                    profile_id=exclusion.profile_id,
                    entity_ref=exclusion.entity_ref,
                    title=exclusion.title,
                    kind=exclusion.kind.value,
                    needs_review=exclusion.needs_review,
                    created_at=exclusion.created_at,
                )
            )

    async def list_for_profile(self, profile_id: UUID) -> list[Exclusion]:
        """The profile's exclusions, oldest first."""
        async with self._sessions() as db:
            rows = await db.scalars(
                select(ExclusionRow)
                .where(ExclusionRow.profile_id == profile_id)
                .order_by(ExclusionRow.created_at)
            )
            return [_exclusion_to_domain(row) for row in rows]

    async def delete(self, profile_id: UUID, exclusion_id: UUID) -> bool:
        """Delete one exclusion of this profile."""
        async with self._sessions() as db, db.begin():
            result = await db.execute(
                delete(ExclusionRow).where(
                    ExclusionRow.id == exclusion_id, ExclusionRow.profile_id == profile_id
                )
            )
            return result.rowcount > 0
