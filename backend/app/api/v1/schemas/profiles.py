"""Request and response schemas for profiles and favourites."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.application.services.profiles import ProfileChanges
from app.domain.models import BIRTH_YEAR_MAX, BIRTH_YEAR_MIN, Favourite, FavouriteKind, Profile

DisplayName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]
BirthYear = Annotated[int, Field(ge=BIRTH_YEAR_MIN, le=BIRTH_YEAR_MAX)]
CountryCode = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^[A-Za-z]{2}$")
]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
TextList = Annotated[list[ShortText], Field(max_length=10)]
FavouriteName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]


class FavouriteOut(BaseModel):
    """A favourite. `verified` is true when it was matched in Qloo, so it can be a signal."""

    id: UUID
    name: str
    kind: FavouriteKind
    qloo_id: str | None
    verified: bool
    song_title: str | None

    @classmethod
    def from_domain(cls, favourite: Favourite) -> Self:
        """Build from the domain entity."""
        return cls(
            id=favourite.id,
            name=favourite.name,
            kind=favourite.kind,
            qloo_id=favourite.qloo_id,
            verified=favourite.verified,
            song_title=favourite.song_title,
        )


class ProfileOut(BaseModel):
    """A profile with its favourites."""

    id: UUID
    display_name: str
    birth_year: int
    country_code: str | None
    places_lived: list[str]
    languages: list[str]
    is_demo: bool
    favourites: list[FavouriteOut]

    @classmethod
    def from_domain(cls, profile: Profile) -> Self:
        """Build from the domain entity."""
        return cls(
            id=profile.id,
            display_name=profile.display_name,
            birth_year=profile.birth_year,
            country_code=profile.country_code,
            places_lived=profile.places_lived,
            languages=profile.languages,
            is_demo=profile.is_demo,
            favourites=[FavouriteOut.from_domain(favourite) for favourite in profile.favourites],
        )


class ProfileCreate(BaseModel):
    """A new profile. Only the display name and birth year are required."""

    display_name: DisplayName
    birth_year: BirthYear
    country_code: CountryCode | None = None
    places_lived: TextList = Field(default_factory=list)
    languages: TextList = Field(default_factory=list)

    def optional_fields(self) -> ProfileChanges:
        """The optional fields, as profile changes."""
        return ProfileChanges(
            country_code=self.country_code,
            places_lived=self.places_lived,
            languages=self.languages,
        )


class ProfileUpdate(BaseModel):
    """Any profile fields. Fields left out stay as they are; `country_code: null` clears it."""

    display_name: DisplayName | None = None
    birth_year: BirthYear | None = None
    country_code: CountryCode | None = None
    places_lived: TextList | None = None
    languages: TextList | None = None

    @model_validator(mode="after")
    def _no_nulls_for_required_fields(self) -> Self:
        for name in ("display_name", "birth_year", "places_lived", "languages"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} can't be null")
        return self

    def changes(self) -> ProfileChanges:
        """Only the fields the request sent."""
        sent: dict[str, object] = self.model_dump(exclude_unset=True)
        return ProfileChanges(**sent)  # type: ignore[typeddict-item]


class FavouriteCreate(BaseModel):
    """A favourite. Send `entity_id` when the caregiver picked a taste-search match."""

    name: FavouriteName
    kind: FavouriteKind
    entity_id: Annotated[str, StringConstraints(min_length=1, max_length=100)] | None = None
    song_title: FavouriteName | None = None

    @model_validator(mode="after")
    def _song_title_only_for_songs(self) -> Self:
        if self.song_title is not None and self.kind is not FavouriteKind.SONG:
            raise ValueError("song_title is only allowed when kind is song")
        return self
