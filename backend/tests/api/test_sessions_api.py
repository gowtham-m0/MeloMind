"""API tests for sessions: planning, the status machine, draft edits, reactions, ownership and
the rate limit. The demo seed's warm-up plans run inline, so drafts exist straight away."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth import SupabaseTokenVerifier
from app.api.deps import get_container, memory_adapters
from app.core.errors import UpstreamError
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from tests.conftest import AuthHeaders, make_container
from tests.fakes import FailingTasteGraph

API = "/api/v1"


def seed(client: TestClient, headers: dict[str, str]) -> str:
    """Margaret's profile ID, from the demo seed."""
    response = client.post(f"{API}/demo/seed", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["profile_ids"][0]


def plan(
    client: TestClient, headers: dict[str, str], profile_id: str, **body: Any
) -> dict[str, Any]:
    response = client.post(
        f"{API}/profiles/{profile_id}/sessions/plan",
        json={"mode": "standard", "target_minutes": 20, **body},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    return response.json()


def act(client: TestClient, headers: dict[str, str], session_id: str, action: str) -> Any:
    return client.post(f"{API}/sessions/{session_id}/{action}", headers=headers)


def react(
    client: TestClient, headers: dict[str, str], session: dict[str, Any], index: int, reaction: str
) -> dict[str, Any]:
    item = session["items"][index]
    response = client.post(
        f"{API}/sessions/{session['id']}/items/{item['id']}/feedback",
        json={"reaction": reaction},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_plan_returns_a_draft_with_sourced_items_and_a_logged_run(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)

    session = plan(client, headers, profile_id)
    run = client.get(f"{API}/agent-runs/{session['agent_run_id']}", headers=headers).json()

    assert session["status"] == "draft"
    assert session["mode"] == "standard"
    assert session["items"]
    assert all(item["source"] == "demo_fixture" and item["reason"] for item in session["items"])
    assert all(item["prompt"] for item in session["items"])
    assert 1080 <= session["total_duration_s"] <= 1320
    assert run["kind"] == "plan" and run["status"] == "done"
    assert run["result"]["session_id"] == session["id"]
    assert {step["node"] for step in run["steps"]} >= {"load_context", "fallback", "guardrails"}


def test_a_rejected_item_is_gone_from_the_next_plan_and_the_shelf(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    first = plan(client, headers, profile_id)
    assert act(client, headers, first["id"], "approve").status_code == 200
    assert act(client, headers, first["id"], "start").status_code == 200
    rejected = first["items"][0]

    effect = react(client, headers, first, 0, "rejected")
    react(client, headers, first, 1, "sang_along")
    second = plan(client, headers, profile_id)
    shelf = client.get(f"{API}/profiles/{profile_id}/shelf", headers=headers).json()
    run = client.get(f"{API}/agent-runs/{second['agent_run_id']}", headers=headers).json()
    messages = [step["message"] for step in run["steps"]]

    assert effect == {
        "ok": True,
        "counted": True,
        "effect": "Rejected. It won't be suggested again.",
    }
    assert rejected["ref"] not in {item["ref"] for item in second["items"]}
    assert rejected["ref"] not in {card["ref"] for card in shelf}
    assert any(rejected["title"] in message and "rejected" in message for message in messages)
    assert any("sang along" in message for message in messages)


def test_upset_hides_the_item_and_queues_it_for_review(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    session = plan(client, headers, profile_id)
    act(client, headers, session["id"], "approve")
    hidden = session["items"][1]

    effect = react(client, headers, session, 1, "upset")
    exclusions = client.get(f"{API}/profiles/{profile_id}/exclusions", headers=headers).json()
    shelf = client.get(f"{API}/profiles/{profile_id}/shelf", headers=headers).json()

    assert effect["effect"] == "Hidden. You can review it later."
    assert [(e["entity_ref"], e["reason"], e["needs_review"]) for e in exclusions] == [
        (hidden["ref"], "upset", True)
    ]
    assert hidden["ref"] not in {card["ref"] for card in shelf}


@pytest.mark.parametrize(
    ("steps", "action"),
    [
        ([], "start"),
        ([], "complete"),
        (["approve"], "approve"),
        (["approve"], "complete"),
        (["approve", "start", "complete"], "start"),
    ],
)
def test_invalid_status_changes_are_409(
    client: TestClient, auth: AuthHeaders, user_id: UUID, steps: list[str], action: str
) -> None:
    headers = auth(user_id)
    session = plan(client, headers, seed(client, headers))
    for step in steps:
        assert act(client, headers, session["id"], step).status_code == 200

    response = act(client, headers, session["id"], action)

    assert response.status_code == 409
    assert response.json()["error"] == "conflict"


def test_the_full_status_path(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    session = plan(client, headers, seed(client, headers))

    statuses = [
        act(client, headers, session["id"], a).json()["status"]
        for a in ("approve", "start", "complete")
    ]
    refreshed = client.get(f"{API}/sessions/{session['id']}", headers=headers).json()

    assert statuses == ["approved", "in_progress", "completed"]
    assert refreshed["status"] == "completed"


def test_a_warmup_set_stops_at_approved(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    history = client.get(f"{API}/profiles/{profile_id}/history", headers=headers).json()
    warmup = next(entry for entry in history if entry["mode"] == "warmup")

    assert warmup["status"] == "draft"
    assert act(client, headers, warmup["id"], "approve").status_code == 200
    assert act(client, headers, warmup["id"], "start").status_code == 409


def test_draft_edits_remove_reorder_and_change_prompts(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    session = plan(client, headers, seed(client, headers))
    ids = [item["id"] for item in session["items"]]
    url = f"{API}/sessions/{session['id']}/items"

    edited = client.patch(
        url,
        json={
            "removed": [ids[0]],
            "order": list(reversed(ids[1:])),
            "prompts": {ids[1]: "  What does this   song bring to mind?  "},
        },
        headers=headers,
    )
    bad_order = client.patch(url, json={"order": ids[1:2]}, headers=headers)
    act(client, headers, session["id"], "approve")
    too_late = client.patch(url, json={"removed": [ids[1]]}, headers=headers)

    assert edited.status_code == 200, edited.text
    items = edited.json()["items"]
    assert [item["id"] for item in items] == list(reversed(ids[1:]))
    assert [item["position"] for item in items] == list(range(len(items)))
    assert items[-1]["prompt"] == "What does this song bring to mind?"
    assert bad_order.status_code == 422
    assert too_late.status_code == 409


def test_unknown_mode_and_length_are_rejected(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    url = f"{API}/profiles/{profile_id}/sessions/plan"

    assert client.post(url, json={"mode": "bridge"}, headers=headers).status_code == 422
    assert client.post(url, json={"target_minutes": 25}, headers=headers).status_code == 422


def test_someone_elses_sessions_runs_and_profile_routes_are_404(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    owner = auth(user_id)
    stranger = auth(uuid4())
    profile_id = seed(client, owner)
    session = plan(client, owner, profile_id)
    item_id = session["items"][0]["id"]

    responses = [
        client.get(f"{API}/sessions/{session['id']}", headers=stranger),
        client.get(f"{API}/agent-runs/{session['agent_run_id']}", headers=stranger),
        client.patch(f"{API}/sessions/{session['id']}/items", json={}, headers=stranger),
        client.post(f"{API}/sessions/{session['id']}/approve", headers=stranger),
        client.post(
            f"{API}/sessions/{session['id']}/items/{item_id}/feedback",
            json={"reaction": "rejected"},
            headers=stranger,
        ),
        client.post(f"{API}/profiles/{profile_id}/sessions/plan", json={}, headers=stranger),
        client.get(f"{API}/profiles/{profile_id}/history", headers=stranger),
        client.get(f"{API}/profiles/{profile_id}/shelf", headers=stranger),
        client.get(f"{API}/profiles/{profile_id}/exclusions", headers=stranger),
        client.post(f"{API}/profiles/{profile_id}/warmup/next", json={}, headers=stranger),
    ]

    assert [response.status_code for response in responses] == [404] * len(responses)
    assert client.get(f"{API}/sessions/{session['id']}", headers=owner).json()["status"] == "draft"


def test_planning_is_rate_limited_per_user(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    for _ in range(10):
        plan(client, headers, profile_id, target_minutes=10)

    response = client.post(f"{API}/profiles/{profile_id}/sessions/plan", json={}, headers=headers)
    other_user = auth(uuid4())
    other_profile = seed(client, other_user)

    assert response.status_code == 429
    assert response.json()["error"] == "rate_limited"
    assert plan(client, other_user, other_profile)["status"] == "draft"


def test_a_qloo_outage_fails_the_plan_cleanly(
    client: TestClient, auth: AuthHeaders, user_id: UUID, verifier: SupabaseTokenVerifier
) -> None:
    broken = make_container(verifier, memory_adapters(FailingTasteGraph()))
    client.app.dependency_overrides[get_container] = lambda: broken  # type: ignore[attr-defined]
    headers = auth(user_id)
    profile = client.post(
        f"{API}/profiles", json={"display_name": "Bob", "birth_year": 1950}, headers=headers
    ).json()

    session = plan(client, headers, profile["id"])
    run = client.get(f"{API}/agent-runs/{session['agent_run_id']}", headers=headers).json()

    assert session["status"] == "failed"
    assert run["status"] == "failed"
    assert any("didn't answer" in step["message"] for step in run["steps"])
    assert run["steps"][-1]["message"] == "Nothing playable was found. Please try again."


def test_a_rejected_item_leaves_drafts_waiting_for_review(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    profile_id = seed(client, headers)
    history = client.get(f"{API}/profiles/{profile_id}/history", headers=headers).json()
    warmup_id = next(entry["id"] for entry in history if entry["mode"] == "warmup")
    warmup = client.get(f"{API}/sessions/{warmup_id}", headers=headers).json()
    session = plan(client, headers, profile_id)
    act(client, headers, session["id"], "approve")
    shared = next(
        index
        for index, item in enumerate(session["items"])
        if item["ref"] in {entry["ref"] for entry in warmup["items"]}
    )
    rejected_ref = session["items"][shared]["ref"]

    react(client, headers, session, shared, "rejected")
    warmup_after = client.get(f"{API}/sessions/{warmup_id}", headers=headers).json()
    session_after = client.get(f"{API}/sessions/{session['id']}", headers=headers).json()

    assert rejected_ref not in {item["ref"] for item in warmup_after["items"]}
    assert [item["position"] for item in warmup_after["items"]] == list(
        range(len(warmup_after["items"]))
    )
    assert rejected_ref in {item["ref"] for item in session_after["items"]}


class BrokenMedia:
    """YouTube refusing every lookup, as when its daily limit is used up."""

    async def resolve(self, query: str) -> None:
        raise UpstreamError("YouTube refused the request.")


def test_without_youtube_the_plan_fails_clearly_instead_of_offering_only_books(
    client: TestClient, auth: AuthHeaders, user_id: UUID, verifier: SupabaseTokenVerifier
) -> None:
    broken = make_container(verifier, memory_adapters(FixtureTasteGraph(), BrokenMedia()))
    client.app.dependency_overrides[get_container] = lambda: broken  # type: ignore[attr-defined]
    headers = auth(user_id)
    profile_id = seed(client, headers)

    session = plan(client, headers, profile_id)
    run = client.get(f"{API}/agent-runs/{session['agent_run_id']}", headers=headers).json()
    messages = [step["message"] for step in run["steps"]]

    assert session["status"] == "failed"
    assert session["items"] == []
    assert any("YouTube didn't answer" in message for message in messages)
    assert messages[-1].startswith("YouTube didn't answer, so there are no videos to play")
