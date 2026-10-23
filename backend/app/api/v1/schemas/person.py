"""Schemas for Person mode: the shelf, the warm-up and the person's signals. Shelf items never
carry a reason or a prompt."""

from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.v1.schemas.sessions import MediaOut, Note
from app.application.services.warmup import WarmupStep
from app.domain.feedback import PersonSignal, Reaction
from app.domain.models import FavouriteKind
from app.domain.sessions import ShelfItem, ShelfOrigin

Ref = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
SHOWN_MAX = 200
PLAYED_MAX_SECONDS = 24 * 60 * 60


class ShelfItemOut(BaseModel):
    """A card: title, type icon, year and decade colour. `from` says why it's on the shelf."""

    model_config = ConfigDict(populate_by_name=True)

    ref: str
    title: str
    entity_type: FavouriteKind
    release_year: int | None
    decade: int | None
    media: MediaOut
    origin: ShelfOrigin = Field(alias="from")

    @classmethod
    def from_domain(cls, card: ShelfItem) -> Self:
        """Build from the domain value."""
        return cls(
            ref=card.ref,
            title=card.title,
            entity_type=card.kind,
            release_year=card.release_year,
            decade=card.decade,
            media=MediaOut.from_domain(card.media),
            origin=card.origin,
        )


class WarmupNextIn(BaseModel):
    """The card just chosen, if any, and every card shown so far."""

    chosen_ref: Ref | None = None
    shown_refs: list[Ref] = Field(default_factory=list, max_length=SHOWN_MAX)


class WarmupNextOut(BaseModel):
    """The next two cards, or `done: true`."""

    pair: list[ShelfItemOut] | None
    done: bool

    @classmethod
    def from_step(cls, step: WarmupStep) -> Self:
        """Build from the service's answer."""
        pair = [ShelfItemOut.from_domain(card) for card in step.pair] if step.pair else None
        return cls(pair=pair, done=step.done)


class PersonSignalIn(BaseModel):
    """A tap in Person mode. Send `played_s` with `skipped`: a skip counts only under 15 s."""

    item_ref: Ref
    signal: PersonSignal
    played_s: int | None = Field(default=None, ge=0, le=PLAYED_MAX_SECONDS)


class RefReactionIn(BaseModel):
    """The caregiver's reaction to a card, by its ref."""

    item_ref: Ref
    reaction: Reaction
    note: Note | None = None
