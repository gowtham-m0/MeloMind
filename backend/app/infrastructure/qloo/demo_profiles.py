"""Reads the sample profiles that `POST /demo/seed` creates, from `demo_profiles.json`."""

import json
from pathlib import Path
from typing import Any

from app.domain.models import (
    DemoFavouriteSpec,
    DemoJournalSpec,
    DemoLinkSpec,
    DemoProfileSpec,
    FavouriteKind,
)

PROFILES_PATH = Path(__file__).with_name("demo_profiles.json")


def _parse_favourite(raw: dict[str, Any]) -> DemoFavouriteSpec:
    return DemoFavouriteSpec(
        name=raw["name"], kind=FavouriteKind(raw["kind"]), song_title=raw.get("song_title")
    )


def _parse_entry(raw: dict[str, Any]) -> DemoJournalSpec:
    return DemoJournalSpec(
        days_ago=raw["days_ago"],
        text=raw["text"],
        mood=raw.get("mood"),
        links=tuple(DemoLinkSpec(name=link["name"], kind=link["kind"]) for link in raw["links"]),
    )


def _parse_profile(raw: dict[str, Any]) -> DemoProfileSpec:
    return DemoProfileSpec(
        key=raw["key"],
        display_name=raw["display_name"],
        birth_year=raw.get("birth_year"),
        country_code=raw.get("country_code"),
        places_lived=tuple(raw.get("places_lived", [])),
        languages=tuple(raw.get("languages", [])),
        favourites=tuple(_parse_favourite(item) for item in raw["favourites"]),
        likes=tuple(_parse_favourite(item) for item in raw.get("likes", [])),
        not_interested=tuple(_parse_favourite(item) for item in raw.get("not_interested", [])),
        journal=tuple(_parse_entry(entry) for entry in raw.get("journal", [])),
    )


def load_demo_profiles(path: Path = PROFILES_PATH) -> list[DemoProfileSpec]:
    """The sample profiles, with favourites by name only. The seed resolves the names."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [_parse_profile(profile) for profile in raw["profiles"]]
