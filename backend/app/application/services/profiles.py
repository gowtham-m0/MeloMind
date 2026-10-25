"""Use cases for profiles and their favourites. Every call is scoped to the signed-in owner."""

from typing import TypedDict
from uuid import UUID

from app.application.ports import JournalRepository, ProfileRepository
from app.core.errors import InvalidInputError, NotFoundError
from app.domain.models import (
    BIRTH_YEAR_MIN,
    Favourite,
    FavouriteKind,
    Profile,
    birth_year_max,
    utc_now,
)

DISPLAY_NAME_MAX = 60
TEXT_ITEM_MAX = 100
TEXT_LIST_MAX = 10
FAVOURITE_NAME_MAX = 120
IMAGE_URL_MAX = 500


class ProfileChanges(TypedDict, total=False):
    """Fields the user can change. Fields left out stay as they are."""

    display_name: str
    birth_year: int | None
    country_code: str | None
    places_lived: list[str]
    languages: list[str]


class ProfileService:
    """Create, read, change and delete profiles and favourites, for their owner only."""

    def __init__(
        self, profiles: ProfileRepository, journal: JournalRepository | None = None
    ) -> None:
        self._profiles = profiles
        self._journal = journal

    async def list(self, owner_id: UUID) -> list[Profile]:
        """Every profile this user owns."""
        return await self._profiles.list_for_owner(owner_id)

    async def get(self, owner_id: UUID, profile_id: UUID) -> Profile:
        """One profile. Someone else's profile is reported as not found."""
        profile = await self._profiles.get(profile_id)
        if profile is None or profile.owner_id != owner_id:
            raise NotFoundError("Profile not found.")
        return profile

    async def create(self, owner_id: UUID, display_name: str, changes: ProfileChanges) -> Profile:
        """A new profile. Only the display name is required."""
        profile = Profile(owner_id=owner_id, display_name=_clean_display_name(display_name))
        _apply(profile, changes)
        await self._profiles.add(profile)
        return profile

    async def update(self, owner_id: UUID, profile_id: UUID, changes: ProfileChanges) -> Profile:
        """Change some of a profile's fields."""
        profile = await self.get(owner_id, profile_id)
        _apply(profile, changes)
        profile.updated_at = utc_now()
        await self._profiles.update(profile)
        return profile

    async def delete(self, owner_id: UUID, profile_id: UUID) -> None:
        """Delete a profile and everything that belongs to it."""
        await self.get(owner_id, profile_id)
        if self._journal is not None:
            await self._journal.delete_for_profile(profile_id)
        await self._profiles.delete(profile_id)

    async def add_favourite(
        self,
        owner_id: UUID,
        profile_id: UUID,
        name: str,
        kind: FavouriteKind,
        entity_id: str | None = None,
        song_title: str | None = None,
        image_url: str | None = None,
    ) -> Favourite:
        """Save a favourite. It's verified when the user picked a match from taste search."""
        profile = await self.get(owner_id, profile_id)
        name = _clean_text(name, FAVOURITE_NAME_MAX, "The favourite's name")
        title = _clean_optional(song_title, FAVOURITE_NAME_MAX, "The song title")
        if title is not None and kind is not FavouriteKind.SONG:
            raise InvalidInputError("Only a song can have a song title.")
        qloo_id = _clean_optional(entity_id, TEXT_ITEM_MAX, "The entity ID")
        existing = next(
            (
                favourite
                for favourite in profile.favourites
                if favourite.kind is kind
                and favourite.song_title == title
                and (favourite.qloo_id == qloo_id if qloo_id else favourite.name == name)
            ),
            None,
        )
        if existing is not None:
            return existing
        favourite = Favourite(
            profile_id=profile.id,
            name=name,
            kind=kind,
            qloo_id=qloo_id,
            song_title=title,
            image_url=_clean_image_url(image_url) if qloo_id else None,
        )
        await self._profiles.add_favourite(favourite)
        return favourite

    async def remove_favourite(self, owner_id: UUID, profile_id: UUID, favourite_id: UUID) -> None:
        """Delete one favourite from a profile."""
        await self.get(owner_id, profile_id)
        if not await self._profiles.delete_favourite(profile_id, favourite_id):
            raise NotFoundError("Favourite not found.")


def _apply(profile: Profile, changes: ProfileChanges) -> None:
    if "display_name" in changes:
        profile.display_name = _clean_display_name(changes["display_name"])
    if "birth_year" in changes:
        profile.birth_year = _check_birth_year(changes["birth_year"])
    if "country_code" in changes:
        profile.country_code = _clean_country_code(changes["country_code"])
    if "places_lived" in changes:
        profile.places_lived = _clean_list(changes["places_lived"], "places")
    if "languages" in changes:
        profile.languages = _clean_list(changes["languages"], "languages")


def _clean_display_name(value: str) -> str:
    return _clean_text(value, DISPLAY_NAME_MAX, "The name")


def _check_birth_year(value: int | None) -> int | None:
    if value is None:
        return None
    latest = birth_year_max()
    if not BIRTH_YEAR_MIN <= value <= latest:
        raise InvalidInputError(f"The birth year must be between {BIRTH_YEAR_MIN} and {latest}.")
    return value


def _clean_image_url(value: str | None) -> str | None:
    """An image URL from taste search: https only, and short (rule 13: URLs only)."""
    if value is None or not value.strip():
        return None
    url = value.strip()
    if not url.startswith("https://") or len(url) > IMAGE_URL_MAX or any(c.isspace() for c in url):
        raise InvalidInputError("The image must be an https URL.")
    return url


def _clean_country_code(value: str | None) -> str | None:
    if value is None:
        return None
    code = value.strip().upper()
    if len(code) != 2 or not code.isascii() or not code.isalpha():
        raise InvalidInputError("The country must be a two-letter ISO code, such as US or IN.")
    return code


def _clean_text(value: str, max_length: int, label: str) -> str:
    text = " ".join(value.split())
    if not text:
        raise InvalidInputError(f"{label} can't be empty.")
    if len(text) > max_length:
        raise InvalidInputError(f"{label} must be at most {max_length} characters.")
    return text


def _clean_optional(value: str | None, max_length: int, label: str) -> str | None:
    if value is None or not value.strip():
        return None
    return _clean_text(value, max_length, label)


def _clean_list(values: list[str], label: str) -> list[str]:
    cleaned = [" ".join(value.split()) for value in values]
    cleaned = list(dict.fromkeys(value for value in cleaned if value))
    if len(cleaned) > TEXT_LIST_MAX:
        raise InvalidInputError(f"Add at most {TEXT_LIST_MAX} {label}.")
    if any(len(value) > TEXT_ITEM_MAX for value in cleaned):
        raise InvalidInputError(f"Each of the {label} must be at most {TEXT_ITEM_MAX} characters.")
    return cleaned
