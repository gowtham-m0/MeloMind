"""API tests for the feed: the snapshot, refresh, item details, feedback, the library, exclusions,
the taste quiz, ownership and the rate limit. Background builds run inline, so a refreshed feed
exists by the time the request returns."""

from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.auth import SupabaseTokenVerifier
from app.api.deps import get_container
from app.main import create_app
from tests.conftest import AuthHeaders, make_container, make_settings

API = "/api/v1"


def leo(client: TestClient, headers: dict[str, str]) -> str:
    """Leo's profile ID, from the demo seed (his first feed is built during the seed)."""
    response = client.post(f"{API}/demo/seed", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["profile_ids"][1]


def feed(client: TestClient, headers: dict[str, str], profile_id: str) -> dict[str, Any]:
    response = client.get(f"{API}/profiles/{profile_id}/feed", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def items(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    found = [snapshot["hero"]] if snapshot["hero"] else []
    return found + [item for row in snapshot["rows"] for item in row["items"]]


def signal(
    client: TestClient, headers: dict[str, str], profile_id: str, item: dict[str, Any], kind: str
) -> dict[str, Any]:
    response = client.post(
        f"{API}/profiles/{profile_id}/feedback",
        json={
            "ref": item["ref"],
            "title": item["title"],
            "entity_type": item["entity_type"],
            "signal": kind,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_the_demo_seed_builds_a_feed_with_cards_reasons_and_links(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    snapshot = feed(client, headers, leo(client, headers))

    assert snapshot["status"] == "done"
    assert snapshot["summary"]
    assert snapshot["taste_tags"]
    assert snapshot["rows"][0]["key"] == "for_you"
    rail = [row for row in snapshot["rows"] if row["placement"] == "rail"]
    assert rail and rail[0]["key"] == "cross_culture"
    refs = [item["ref"] for item in items(snapshot)]
    assert len(refs) == len(set(refs))
    for item in items(snapshot):
        assert item["reason"]
        assert item["source"] == "demo_fixture"
        assert item["links"]
        assert item["image_aspect"] in ("square", "poster")
        assert item["liked"] is False


def test_refresh_returns_a_building_feed_and_the_run_logs_it(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)

    response = client.post(f"{API}/profiles/{profile_id}/feed/refresh", headers=headers)

    assert response.status_code == 202
    run_id = response.json()["agent_run_id"]
    run = client.get(f"{API}/agent-runs/{run_id}", headers=headers).json()
    assert run["kind"] == "feed"
    assert run["status"] == "done"
    assert run["steps"][0]["node"] == "load_context"
    assert feed(client, headers, profile_id)["agent_run_id"] == run_id


def test_a_new_profile_has_no_feed_until_refreshed(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile = client.post(f"{API}/profiles", json={"display_name": "Sam"}, headers=headers).json()

    missing = client.get(f"{API}/profiles/{profile['id']}/feed", headers=headers)
    client.post(f"{API}/profiles/{profile['id']}/feed/refresh", headers=headers)

    assert missing.status_code == 404
    assert profile["birth_year"] is None
    assert items(feed(client, headers, profile["id"]))


def test_likes_mark_the_feed_stale_and_show_as_liked(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    first = items(feed(client, headers, profile_id))[1]

    effect = signal(client, headers, profile_id, first, "liked")
    signal(client, headers, profile_id, first, "saved")

    assert effect["counted"] and effect["stale"]
    snapshot = feed(client, headers, profile_id)
    assert snapshot["stale"] is True
    shown = next(item for item in items(snapshot) if item["ref"] == first["ref"])
    assert shown["liked"] and shown["saved"]
    library = client.get(f"{API}/profiles/{profile_id}/library", headers=headers).json()
    assert [item["ref"] for item in library["liked"]] == [first["ref"]]
    assert [item["ref"] for item in library["saved"]] == [first["ref"]]


def test_not_interested_removes_the_item_at_once_and_for_good(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    snapshot = feed(client, headers, profile_id)
    gone = snapshot["rows"][0]["items"][0]
    other = snapshot["rows"][0]["items"][1]

    signal(client, headers, profile_id, gone, "not_interested")

    assert gone["ref"] not in {item["ref"] for item in items(feed(client, headers, profile_id))}
    client.post(f"{API}/profiles/{profile_id}/feed/refresh", headers=headers)
    assert gone["ref"] not in {item["ref"] for item in items(feed(client, headers, profile_id))}
    detail = client.get(f"{API}/profiles/{profile_id}/items/{other['ref']}", headers=headers)
    assert gone["ref"] not in {item["ref"] for item in detail.json()["more_like_this"]}
    blocked = client.get(f"{API}/profiles/{profile_id}/items/{gone['ref']}", headers=headers)
    assert blocked.status_code == 404


def test_not_interested_can_be_undone(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    gone = items(feed(client, headers, profile_id))[2]
    signal(client, headers, profile_id, gone, "not_interested")
    url = f"{API}/profiles/{profile_id}/exclusions"

    listed = client.get(url, headers=headers).json()
    remaining = client.delete(f"{url}/{listed[0]['id']}", headers=headers)

    assert [entry["entity_ref"] for entry in listed] == [gone["ref"]]
    assert remaining.status_code == 200
    assert remaining.json() == []
    detail = client.get(f"{API}/profiles/{profile_id}/items/{gone['ref']}", headers=headers)
    assert detail.status_code == 200


def test_item_detail_has_more_like_this_and_no_preview_without_youtube(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    item = feed(client, headers, profile_id)["rows"][0]["items"][0]

    detail = client.get(f"{API}/profiles/{profile_id}/items/{item['ref']}", headers=headers)
    preview = client.post(
        f"{API}/profiles/{profile_id}/items/{item['ref']}/preview", headers=headers
    )

    assert detail.status_code == 200
    body = detail.json()
    assert body["ref"] == item["ref"]
    assert body["preview_available"] is False
    assert all(more["ref"] != item["ref"] for more in body["more_like_this"])
    assert preview.status_code == 404


def test_opened_counts_once_a_day_and_does_not_mark_the_feed_stale(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    item = items(feed(client, headers, profile_id))[0]

    first = signal(client, headers, profile_id, item, "opened")
    again = signal(client, headers, profile_id, item, "opened")

    assert first["counted"] and not first["stale"]
    assert not again["counted"]


def test_the_client_cannot_send_app_only_signals(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)

    response = client.post(
        f"{API}/profiles/{profile_id}/feedback",
        json={"ref": "x", "title": "X", "signal": "quiz_pick"},
        headers=headers,
    )

    assert response.status_code == 422


def test_the_taste_quiz_pairs_two_types_and_records_picks(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    url = f"{API}/profiles/{profile_id}/quiz/next"

    first = client.post(url, json={"shown_refs": []}, headers=headers).json()
    shown = [item["ref"] for item in first["pair"]]
    second = client.post(
        url, json={"picked_ref": shown[0], "shown_refs": shown}, headers=headers
    ).json()
    wrong = client.post(url, json={"picked_ref": "nope", "shown_refs": shown}, headers=headers)

    assert first["round"] == 1 and first["rounds"] == 6 and not first["done"]
    assert first["pair"][0]["entity_type"] != first["pair"][1]["entity_type"]
    assert second["round"] == 2
    assert not {item["ref"] for item in second["pair"]} & set(shown)
    assert wrong.status_code == 422
    assert feed(client, headers, profile_id)["stale"] is True


def test_other_users_get_404_everywhere(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    profile_id = leo(client, auth(user_id))
    item = items(feed(client, auth(user_id), profile_id))[0]
    stranger = auth(uuid4())
    base = f"{API}/profiles/{profile_id}"

    assert client.get(f"{base}/feed", headers=stranger).status_code == 404
    assert client.post(f"{base}/feed/refresh", headers=stranger).status_code == 404
    assert client.get(f"{base}/items/{item['ref']}", headers=stranger).status_code == 404
    assert client.get(f"{base}/library", headers=stranger).status_code == 404
    assert client.get(f"{base}/exclusions", headers=stranger).status_code == 404
    assert (
        client.post(f"{base}/quiz/next", json={"shown_refs": []}, headers=stranger).status_code
        == 404
    )
    response = client.post(
        f"{base}/feedback",
        json={"ref": item["ref"], "title": item["title"], "signal": "liked"},
        headers=stranger,
    )
    assert response.status_code == 404


def test_refresh_is_rate_limited(verifier: SupabaseTokenVerifier, auth: AuthHeaders) -> None:
    container = make_container(verifier)
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    headers = auth(uuid4())
    with TestClient(app) as client:
        profile_id = leo(client, headers)
        statuses = [
            client.post(f"{API}/profiles/{profile_id}/feed/refresh", headers=headers).status_code
            for _ in range(21)
        ]

    assert statuses[:20] == [202] * 20
    assert statuses[20] == 429


def test_the_quiz_follows_the_profiles_favourites(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = leo(client, headers)
    profile = client.get(f"{API}/profiles/{profile_id}", headers=headers).json()
    loved = {favourite["name"] for favourite in profile["favourites"]}

    pair = client.post(
        f"{API}/profiles/{profile_id}/quiz/next", json={"shown_refs": []}, headers=headers
    ).json()["pair"]

    assert all(item["reason"].startswith("Because you like") for item in pair)
    assert not {item["title"] for item in pair} & loved


def test_the_quiz_for_a_new_profile_uses_popular_titles(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    created = client.post(
        f"{API}/profiles", json={"display_name": "New", "country_code": "IN"}, headers=headers
    ).json()

    pair = client.post(
        f"{API}/profiles/{created['id']}/quiz/next", json={"shown_refs": []}, headers=headers
    ).json()["pair"]

    assert pair is not None
    assert all(item["reason"] == "Popular right now." for item in pair)
