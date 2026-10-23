"""Checks on the hand-written Qloo demo fixtures: labelled as demo data and consistent."""

import json
from pathlib import Path
from typing import Any

import pytest

FIXTURES_DIR = Path(__file__).parents[2] / "app" / "infrastructure" / "qloo" / "fixtures"
FIXTURE_FILES = ["profiles.json", "entities.json", "insights.json", "tags.json"]
ENTITY_TYPES = {"urn:entity:artist", "urn:entity:movie", "urn:entity:tv_show", "urn:entity:book"}
# A song favourite's name is its singer, so it resolves to an artist.
FAVOURITE_KINDS = {
    "artist": "urn:entity:artist",
    "song": "urn:entity:artist",
    "movie": "urn:entity:movie",
    "tv_show": "urn:entity:tv_show",
    "book": "urn:entity:book",
}
MIN_IN_ERA_ITEMS = 8


def load(name: str) -> dict[str, Any]:
    """Read one fixture file."""
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def entities() -> list[dict[str, Any]]:
    return load("entities.json")["entities"]


def names_of(entity: dict[str, Any]) -> set[str]:
    return {entity["name"].casefold(), *(alias.casefold() for alias in entity.get("aliases", []))}


@pytest.mark.parametrize("name", FIXTURE_FILES)
def test_every_file_is_marked_demo(name: str) -> None:
    assert load(name)["demo"] is True


def test_entity_ids_are_unique_and_demo_prefixed() -> None:
    ids = [entity["entity_id"] for entity in entities()]
    assert len(ids) == len(set(ids))
    assert all(entity_id.startswith("demo-") for entity_id in ids)


def test_entities_have_valid_fields() -> None:
    tag_ids = {tag["tag_id"] for tag in load("tags.json")["tags"]}
    for entity in entities():
        assert entity["type"] in ENTITY_TYPES, entity["entity_id"]
        assert 0 <= entity["popularity"] <= 1, entity["entity_id"]
        assert 1900 <= entity["release_year"] <= 2000, entity["entity_id"]
        assert set(entity["tags"]) <= tag_ids, entity["entity_id"]


def test_tag_ids_are_unique_and_demo_prefixed() -> None:
    ids = [tag["tag_id"] for tag in load("tags.json")["tags"]]
    assert len(ids) == len(set(ids))
    assert all(tag_id.startswith("demo-tag-") for tag_id in ids)


def test_insights_reference_known_entities_only() -> None:
    known = {entity["entity_id"] for entity in entities()}
    for signal, related in load("insights.json")["related"].items():
        assert signal in known
        related_ids = [item["entity_id"] for item in related]
        assert signal not in related_ids
        assert len(related_ids) == len(set(related_ids))
        assert set(related_ids) <= known
        assert all(0 <= item["affinity"] <= 1 for item in related)


def test_every_favourite_resolves_to_one_entity_with_insights() -> None:
    related = load("insights.json")["related"]
    for profile in load("profiles.json")["profiles"]:
        for favourite in profile["favourites"]:
            expected_type = FAVOURITE_KINDS[favourite["kind"]]
            matches = [
                entity
                for entity in entities()
                if entity["type"] == expected_type
                and favourite["name"].casefold() in names_of(entity)
            ]
            assert len(matches) == 1, favourite["name"]
            assert matches[0]["entity_id"] in related, favourite["name"]


def test_each_profile_has_enough_items_from_its_youth() -> None:
    for profile in load("profiles.json")["profiles"]:
        start, end = profile["birth_year"] + 13, profile["birth_year"] + 21
        in_era = [
            entity
            for entity in entities()
            if entity["type"] != "urn:entity:artist"
            and entity["country"] == profile["country_code"]
            and start <= entity["release_year"] <= end
        ]
        assert len(in_era) >= MIN_IN_ERA_ITEMS, profile["display_name"]
