"""API tests for Person mode: the shelf shows only approved items, the warm-up, and the person's
signals (shelf items only, a skip only under 15 seconds, once per item per day)."""

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from tests.api.test_sessions_api import API, act, plan, seed
from tests.conftest import AuthHeaders


def shelf(client: TestClient, headers: dict[str, str], profile_id: str) -> list[dict[str, Any]]:
    response = client.get(f"{API}/profiles/{profile_id}/shelf", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def warmup_id(client: TestClient, headers: dict[str, str], profile_id: str) -> str:
    history = client.get(f"{API}/profiles/{profile_id}/history", headers=headers).json()
    return next(entry["id"] for entry in history if entry["mode"] == "warmup")


def next_pair(
    client: TestClient,
    headers: dict[str, str],
    profile_id: str,
    chosen: str | None,
    shown: list[str],
) -> Any:
    return client.post(
        f"{API}/profiles/{profile_id}/warmup/next",
        json={"chosen_ref": chosen, "shown_refs": shown},
        headers=headers,
    )


def signal(
    client: TestClient, headers: dict[str, str], profile_id: str, ref: str, kind: str, **extra: Any
) -> Any:
    return client.post(
        f"{API}/profiles/{profile_id}/person-signals",
        json={"item_ref": ref, "signal": kind, **extra},
        headers=headers,
    )


def test_the_shelf_shows_only_approved_items_and_never_ai_text(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    draft = plan(client, headers, profile_id)

    before = shelf(client, headers, profile_id)
    act(client, headers, draft["id"], "approve")
    act(client, headers, warmup_id(client, headers, profile_id), "approve")
    after = shelf(client, headers, profile_id)

    assert {card["from"] for card in before} == {"favourite"}
    # A ref is shown once: an item in both the session and the warm-up set appears as warm-up.
    assert {card["from"] for card in after} >= {"favourite", "warmup"}
    playable = {item["ref"] for item in draft["items"] if item["media"]}
    assert playable <= {card["ref"] for card in after}
    assert all("reason" not in card and "prompt" not in card for card in after)
    assert all(card["media"] and card["entity_type"] != "book" for card in after)


def test_the_warmup_needs_an_approved_set(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)

    response = next_pair(client, headers, profile_id, None, [])

    assert response.status_code == 409


def test_the_warmup_pairs_differ_record_choices_and_stop(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    act(client, headers, warmup_id(client, headers, profile_id), "approve")
    shown: list[str] = []
    chosen: str | None = None
    pairs: list[list[dict[str, Any]]] = []

    for _ in range(10):
        step = next_pair(client, headers, profile_id, chosen, shown).json()
        if step["done"]:
            break
        pair = step["pair"]
        pairs.append(pair)
        shown += [card["ref"] for card in pair]
        chosen = pair[0]["ref"]

    first_a, first_b = pairs[0]
    assert (first_a["entity_type"], first_a["decade"]) != (
        first_b["entity_type"],
        first_b["decade"],
    )
    assert len(pairs) <= 6
    assert len(set(shown)) == len(shown)
    assert all(card["from"] == "warmup" for pair in pairs for card in pair)
    repeat = signal(client, headers, profile_id, pairs[0][0]["ref"], "chose")
    assert repeat.json()["counted"] is False


def test_signals_count_only_for_shelf_items(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    draft = plan(client, headers, profile_id)

    response = signal(client, headers, profile_id, draft["items"][0]["ref"], "loved")

    assert response.status_code == 422


def test_a_late_skip_is_ignored_and_a_repeat_tap_counts_once(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    ref = shelf(client, headers, profile_id)[0]["ref"]

    late = signal(client, headers, profile_id, ref, "skipped", played_s=15).json()
    quick = signal(client, headers, profile_id, ref, "skipped", played_s=3).json()
    loved = signal(client, headers, profile_id, ref, "loved").json()
    again = signal(client, headers, profile_id, ref, "loved").json()

    assert late["counted"] is False
    assert quick["counted"] is True
    assert loved["counted"] is True
    assert again == {"ok": True, "counted": False, "effect": "Already counted today."}


def test_the_caregiver_can_hide_a_card_from_person_mode(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    card = shelf(client, headers, profile_id)[0]

    response = client.post(
        f"{API}/profiles/{profile_id}/reactions",
        json={"item_ref": card["ref"], "reaction": "upset"},
        headers=headers,
    )
    unknown = client.post(
        f"{API}/profiles/{profile_id}/reactions",
        json={"item_ref": "not-an-item", "reaction": "upset"},
        headers=headers,
    )

    assert response.json()["effect"] == "Hidden. You can review it later."
    assert card["ref"] not in {entry["ref"] for entry in shelf(client, headers, profile_id)}
    assert unknown.status_code == 404


def test_a_hidden_item_can_come_back_but_a_rejection_is_for_good(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    first, second = shelf(client, headers, profile_id)[:2]
    url = f"{API}/profiles/{profile_id}/exclusions"

    hidden = client.post(
        url,
        json={"entity_ref": first["ref"], "title": first["title"], "reason": "upset"},
        headers=headers,
    )
    rejected = client.post(
        url,
        json={"entity_ref": second["ref"], "title": second["title"], "reason": "rejected"},
        headers=headers,
    ).json()
    still_rejected = client.post(
        url,
        json={"entity_ref": second["ref"], "title": second["title"], "reason": "upset"},
        headers=headers,
    ).json()
    refs_while_excluded = {entry["ref"] for entry in shelf(client, headers, profile_id)}
    unhidden = client.delete(f"{url}/{hidden.json()[0]['id']}", headers=headers)
    unreject = client.delete(f"{url}/{rejected[-1]['id']}", headers=headers)
    refs_after = {entry["ref"] for entry in shelf(client, headers, profile_id)}

    assert hidden.status_code == 201
    assert [entry["reason"] for entry in still_rejected] == ["upset", "rejected"]
    assert not {first["ref"], second["ref"]} & refs_while_excluded
    assert [entry["reason"] for entry in unhidden.json()] == ["rejected"]
    assert unreject.status_code == 409
    assert first["ref"] in refs_after
    assert second["ref"] not in refs_after
