"""Reads the sample profiles that `POST /demo/seed` creates, from `fixtures/profiles.json`."""

import json
from pathlib import Path
from typing import Any

from app.domain.models import DemoFavouriteSpec, DemoProfileSpec, FavouriteKind
from app.infrastructure.qloo.fixture_taste_graph import FIXTURES_DIR


def _parse_favourite(raw: dict[str, Any]) -> DemoFavouriteSpec:
    return DemoFavouriteSpec(
        name=raw["name"], kind=FavouriteKind(raw["kind"]), song_title=raw.get("song_title")
    )


def _parse_profile(raw: dict[str, Any]) -> DemoProfileSpec:
    return DemoProfileSpec(
        key=raw["key"],
        display_name=raw["display_name"],
        birth_year=raw["birth_year"],
        country_code=raw.get("country_code"),
        places_lived=tuple(raw.get("places_lived", [])),
        languages=tuple(raw.get("languages", [])),
        favourites=tuple(_parse_favourite(item) for item in raw["favourites"]),
    )


def load_demo_profiles(fixtures_dir: Path = FIXTURES_DIR) -> list[DemoProfileSpec]:
    """The sample profiles, with favourites by name only. The seed resolves the names."""
    raw = json.loads((fixtures_dir / "profiles.json").read_text(encoding="utf-8"))
    return [_parse_profile(profile) for profile in raw["profiles"]]
