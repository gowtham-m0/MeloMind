"""API tests for the journal, the taste page and the favourite resolver: entries, suggestions,
confirming and rejecting, signals, privacy, voice notes, the taste map and ownership. Background
runs happen inline, so a link run has finished by the time its request returns."""

import asyncio
from collections.abc import Iterator
from dataclasses import replace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.auth import SupabaseTokenVerifier
from app.api.deps import Adapters, get_container, memory_adapters
from app.application.agent.prompts.extract import ExtractedMention, ExtractOutput
from app.application.agent.prompts.interpret import Interpretation
from app.infrastructure.qloo.fixture_taste_graph import FixtureTasteGraph
from app.main import create_app
from tests.conftest import AuthHeaders, make_container, make_settings
from tests.fakes import FakeLanguageModel, FakeSpeech, RecordingTasteGraph

API = "/api/v1"
ENTRY = "Rewatched Interstellar with my brother Arjun, then had Glass Animals on repeat."


def read_entry(schema: type[BaseModel], prompt: str) -> BaseModel:
    """A scripted reader: what a good model finds in ENTRY, plus a made-up title that isn't in
    the text (the code must drop it) and a low-confidence guess."""
    assert schema is ExtractOutput
    return ExtractOutput(
        mentions=[
            ExtractedMention(kind="movie", text="Interstellar", confidence=0.95),
            ExtractedMention(kind="artist", text="Glass Animals", confidence=0.9),
            ExtractedMention(kind="movie", text="Inception", confidence=0.9),
            ExtractedMention(kind="artist", text="Arjun", confidence=0.2),
        ],
        mood="nostalgic",
    )


class Stack:
    """A client over services with a scripted journal reader and fake speech."""

    def __init__(self, client: TestClient, adapters: Adapters, taste: RecordingTasteGraph):
        self.client = client
        self.adapters = adapters
        self.taste = taste


@pytest.fixture
def stack(verifier: SupabaseTokenVerifier) -> Iterator[Stack]:
    taste = RecordingTasteGraph(FixtureTasteGraph())
    adapters = memory_adapters(
        taste, journal_language_model=FakeLanguageModel(read_entry), speech=FakeSpeech()
    )
    container = make_container(verifier, adapters)
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    with TestClient(app) as client:
        yield Stack(client, adapters, taste)


def new_profile(client: TestClient, headers: dict[str, str]) -> str:
    response = client.post(f"{API}/profiles", json={"display_name": "Aanya"}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def write(client: TestClient, headers: dict[str, str], profile_id: str, text: str) -> Any:
    response = client.post(
        f"{API}/profiles/{profile_id}/journal", json={"text": text}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def get_entry(client: TestClient, headers: dict[str, str], pid: str, entry_id: str) -> Any:
    response = client.get(f"{API}/profiles/{pid}/journal/{entry_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def decide(client: TestClient, headers: dict[str, str], pid: str, link_id: str, status: str) -> Any:
    return client.patch(
        f"{API}/profiles/{pid}/journal/links/{link_id}", json={"status": status}, headers=headers
    )


def signals(stack: Stack, profile_id: str) -> list[Any]:
    return asyncio.run(stack.adapters.feedback.list_for_profile(UUID(profile_id)))


def test_an_entry_gets_suggestions_for_the_film_and_artist_and_no_person(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)

    run = stack.client.get(f"{API}/agent-runs/{created['link_run_id']}", headers=headers).json()
    entry = get_entry(stack.client, headers, pid, created["id"])

    assert run["kind"] == "link" and run["status"] == "done"
    found = {(s["target"]["title"], s["target"]["kind"]) for s in entry["suggestions"]}
    assert found == {("Interstellar", "movie"), ("Glass Animals", "artist")}
    assert entry["links"] == []
    assert all(s["status"] == "suggested" and s["reason"] for s in entry["suggestions"])


def test_journal_text_never_reaches_qloo_or_the_log(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)

    run = stack.client.get(f"{API}/agent-runs/{created['link_run_id']}", headers=headers).json()
    messages = " ".join(step["message"] for step in run["steps"])

    assert stack.taste.searches
    for query in stack.taste.searches:
        assert query in ("Interstellar", "Glass Animals") or "brother" not in query
        assert ENTRY not in query and "Arjun" not in query
    assert "brother" not in messages and "Arjun" not in messages and ENTRY not in messages


def test_suggested_links_change_nothing_until_confirmed(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    write(stack.client, headers, pid, ENTRY)

    taste_map = stack.client.get(f"{API}/profiles/{pid}/taste/map", headers=headers).json()
    taste = stack.client.get(f"{API}/profiles/{pid}/taste", headers=headers).json()

    assert signals(stack, pid) == []
    assert taste_map == {"nodes": [], "links": []}
    assert taste["by_type"] == {}


def test_confirming_adds_a_signal_and_shapes_the_feed_and_map(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)

    confirmed = stack.client.post(
        f"{API}/profiles/{pid}/journal/{created['id']}/links/confirm-all", headers=headers
    ).json()
    stack.client.post(f"{API}/profiles/{pid}/feed/refresh", headers=headers)
    snapshot = stack.client.get(f"{API}/profiles/{pid}/feed", headers=headers).json()
    taste_map = stack.client.get(f"{API}/profiles/{pid}/taste/map", headers=headers).json()

    assert len(confirmed["links"]) == 2 and confirmed["suggestions"] == []
    kinds = sorted(entry.kind.value for entry in signals(stack, pid))
    assert kinds == ["journal_confirmed", "journal_confirmed"]
    assert any(row["key"] == "journal" for row in snapshot["rows"])
    titles = {node["title"] for node in taste_map["nodes"]}
    assert {"Interstellar", "Glass Animals"} <= titles
    assert {link["kind"] for link in taste_map["links"]} == {"mentions"}
    assert all(set(link) == {"from", "to", "kind"} for link in taste_map["links"])


def test_confirming_marks_the_feed_stale(stack: Stack, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    stack.client.post(
        f"{API}/profiles/{pid}/favourites",
        json={"name": "Dune", "kind": "movie", "entity_id": "demo-movie-dune"},
        headers=headers,
    )
    stack.client.post(f"{API}/profiles/{pid}/feed/refresh", headers=headers)
    created = write(stack.client, headers, pid, ENTRY)

    link_id = created["suggestions"][0]["id"]
    assert decide(stack.client, headers, pid, link_id, "confirmed").status_code == 200
    snapshot = stack.client.get(f"{API}/profiles/{pid}/feed", headers=headers).json()

    assert snapshot["stale"] is True


def test_rejecting_adds_nothing_stays_rejected_and_is_never_suggested_again(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)
    film = next(s for s in created["suggestions"] if s["target"]["title"] == "Interstellar")

    rejected = decide(stack.client, headers, pid, film["id"], "rejected")
    again = decide(stack.client, headers, pid, film["id"], "confirmed")
    edited = stack.client.patch(
        f"{API}/profiles/{pid}/journal/{created['id']}",
        json={"text": ENTRY + " Interstellar again tomorrow."},
        headers=headers,
    ).json()
    entry = get_entry(stack.client, headers, pid, created["id"])

    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert again.status_code == 409
    assert edited["link_run_id"] is not None
    assert signals(stack, pid) == []
    titles = [s["target"]["title"] for s in entry["suggestions"] + entry["links"]]
    assert "Interstellar" not in titles


def test_deleting_an_entry_removes_its_links_and_signals(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)
    stack.client.post(
        f"{API}/profiles/{pid}/journal/{created['id']}/links/confirm-all", headers=headers
    )

    deleted = stack.client.delete(f"{API}/profiles/{pid}/journal/{created['id']}", headers=headers)
    listing = stack.client.get(f"{API}/profiles/{pid}/journal", headers=headers).json()
    taste_map = stack.client.get(f"{API}/profiles/{pid}/taste/map", headers=headers).json()

    assert deleted.status_code == 204
    assert listing == []
    assert signals(stack, pid) == []
    assert taste_map["nodes"] == []


def test_deleting_a_profile_deletes_its_journal(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    write(stack.client, headers, pid, ENTRY)

    stack.client.delete(f"{API}/profiles/{pid}", headers=headers)
    journal = stack.adapters.journal

    assert asyncio.run(journal.list_nodes(UUID(pid))) == []
    assert asyncio.run(journal.list_links(UUID(pid))) == []


def test_someone_elses_journal_is_not_found(stack: Stack, auth: AuthHeaders, user_id: UUID) -> None:
    owner = auth(user_id)
    stranger = auth(uuid4())
    pid = new_profile(stack.client, owner)
    created = write(stack.client, owner, pid, ENTRY)
    link_id = created["suggestions"][0]["id"]
    base = f"{API}/profiles/{pid}"

    responses = [
        stack.client.get(f"{base}/journal", headers=stranger),
        stack.client.post(f"{base}/journal", json={"text": "hi"}, headers=stranger),
        stack.client.get(f"{base}/journal/{created['id']}", headers=stranger),
        stack.client.delete(f"{base}/journal/{created['id']}", headers=stranger),
        stack.client.patch(
            f"{base}/journal/links/{link_id}", json={"status": "confirmed"}, headers=stranger
        ),
        stack.client.get(f"{base}/taste", headers=stranger),
        stack.client.get(f"{base}/taste/map", headers=stranger),
        stack.client.post(f"{base}/favourites/resolve", json={"text": "x"}, headers=stranger),
    ]

    assert [response.status_code for response in responses] == [404] * len(responses)


def test_entry_validation(stack: Stack, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    url = f"{API}/profiles/{pid}/journal"

    assert stack.client.post(url, json={"text": ""}, headers=headers).status_code == 422
    assert stack.client.post(url, json={"text": "x" * 5001}, headers=headers).status_code == 422
    future = stack.client.post(url, json={"text": "hi", "date": "2999-01-01"}, headers=headers)
    assert future.status_code == 422


def test_transcribe_returns_text_and_rejects_bad_files(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    url = f"{API}/profiles/{pid}/journal/transcribe"

    good = stack.client.post(
        url, content=b"\x1a\x45audio", headers={**headers, "Content-Type": "audio/webm;codecs=opus"}
    )
    wrong_type = stack.client.post(
        url, content=b"text", headers={**headers, "Content-Type": "text/plain"}
    )
    empty = stack.client.post(url, content=b"", headers={**headers, "Content-Type": "audio/ogg"})
    too_big = stack.client.post(
        url,
        content=b"0" * (10 * 1024 * 1024 + 1),
        headers={**headers, "Content-Type": "audio/wav"},
    )

    assert good.status_code == 200 and good.json() == {"text": "Rewatched Interstellar."}
    assert [wrong_type.status_code, empty.status_code, too_big.status_code] == [422, 422, 422]
    listing = stack.client.get(f"{API}/profiles/{pid}/journal", headers=headers).json()
    assert listing == []


def test_a_failed_transcription_is_a_502_and_stores_nothing(
    verifier: SupabaseTokenVerifier, auth: AuthHeaders, user_id: UUID
) -> None:
    adapters = memory_adapters(FixtureTasteGraph(), speech=FakeSpeech(fail=True))
    container = make_container(verifier, adapters)
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    headers = auth(user_id)
    with TestClient(app) as client:
        pid = new_profile(client, headers)
        response = client.post(
            f"{API}/profiles/{pid}/journal/transcribe",
            content=b"audio",
            headers={**headers, "Content-Type": "audio/webm"},
        )
        listing = client.get(f"{API}/profiles/{pid}/journal", headers=headers).json()

    assert response.status_code == 502
    assert listing == []


def test_without_an_ai_reader_the_journal_spots_things_you_love(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(client, headers)
    client.post(
        f"{API}/profiles/{pid}/favourites",
        json={"name": "Glass Animals", "kind": "artist", "entity_id": "demo-artist-glass-animals"},
        headers=headers,
    )
    created = write(client, headers, pid, ENTRY)

    assert [s["target"]["title"] for s in created["suggestions"]] == ["Glass Animals"]


def test_the_demo_journal_is_seeded_with_confirmed_links(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    aanya = client.post(f"{API}/demo/seed", headers=headers).json()["profile_ids"][0]

    entries = client.get(f"{API}/profiles/{aanya}/journal", headers=headers).json()
    snapshot = client.get(f"{API}/profiles/{aanya}/feed", headers=headers).json()
    taste = client.get(f"{API}/profiles/{aanya}/taste", headers=headers).json()

    assert len(entries) == 4
    assert all(entry["links"] and entry["suggestions"] == [] for entry in entries)
    assert any(row["key"] == "journal" for row in snapshot["rows"])
    assert taste["sentence"].startswith("You love")
    assert taste["top_tags"] and taste["by_type"]["tv_show"] >= 1


def test_the_taste_map_respects_its_cap(
    verifier: SupabaseTokenVerifier, auth: AuthHeaders, user_id: UUID
) -> None:
    container = make_container(verifier)
    container.taste_profile._max_map_nodes = 5
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    headers = auth(user_id)
    with TestClient(app) as client:
        aanya = client.post(f"{API}/demo/seed", headers=headers).json()["profile_ids"][0]
        taste_map = client.get(f"{API}/profiles/{aanya}/taste/map", headers=headers).json()

    ids = {node["id"] for node in taste_map["nodes"]}
    assert len(ids) == 5
    assert all(link["from"] in ids and link["to"] in ids for link in taste_map["links"])


def resolve(client: TestClient, headers: dict[str, str], pid: str, body: dict[str, Any]) -> Any:
    response = client.post(f"{API}/profiles/{pid}/favourites/resolve", json=body, headers=headers)
    assert response.status_code == 202, response.text
    run_id = response.json()["agent_run_id"]
    return client.get(f"{API}/agent-runs/{run_id}", headers=headers).json()


def test_resolve_finds_a_typed_name(client: TestClient, auth: AuthHeaders, user_id: UUID) -> None:
    headers = auth(user_id)
    pid = new_profile(client, headers)

    run = resolve(client, headers, pid, {"text": "To Kill a Mockingbird", "kind": "book"})

    assert run["kind"] == "resolve" and run["status"] == "done"
    proposals = run["result"]["proposals"]
    assert [(p["name"], p["type"]) for p in proposals] == [("To Kill a Mockingbird", "book")]


def test_resolve_asks_for_a_hint_and_never_stores_a_lyric(
    client: TestClient, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(client, headers)
    lyric = "sometimes all I think about is you late nights in the middle of June"

    run = resolve(client, headers, pid, {"text": lyric, "kind": "song"})
    hinted = resolve(client, headers, pid, {"text": lyric, "kind": "song", "hint": "Glass Animals"})

    assert run["status"] == "needs_hint" and run["result"]["question"]
    assert lyric not in str(run) and "middle of June" not in str(hinted)
    assert hinted["status"] == "done"
    proposal = hinted["result"]["proposals"][0]
    # A lyric is never kept as the song title, so the singer is proposed as an artist.
    assert (proposal["name"], proposal["kind"], proposal["song_title"]) == (
        "Glass Animals",
        "artist",
        None,
    )


def test_resolve_uses_the_interpretation_and_checks_the_type(
    verifier: SupabaseTokenVerifier, auth: AuthHeaders, user_id: UUID
) -> None:
    def interpret(schema: type[BaseModel], prompt: str) -> BaseModel:
        return Interpretation(kind="song", song_title="Heat Waves", singer="Glass Animals")

    taste = RecordingTasteGraph(FixtureTasteGraph())
    adapters = replace(memory_adapters(taste), language_model=FakeLanguageModel(interpret))
    container = make_container(verifier, adapters)
    app = create_app(make_settings())
    app.dependency_overrides[get_container] = lambda: container
    headers = auth(user_id)
    with TestClient(app) as client:
        pid = new_profile(client, headers)
        run = resolve(client, headers, pid, {"text": "that heat waves song"})

    proposal = run["result"]["proposals"][0]
    assert (proposal["name"], proposal["song_title"]) == ("Glass Animals", "Heat Waves")
    assert "Heat Waves" not in taste.searches and "that heat waves song" not in taste.searches


def test_a_confirmed_journal_item_opens_in_the_detail_sheet(
    stack: Stack, auth: AuthHeaders, user_id: UUID
) -> None:
    headers = auth(user_id)
    pid = new_profile(stack.client, headers)
    created = write(stack.client, headers, pid, ENTRY)
    stack.client.post(
        f"{API}/profiles/{pid}/journal/{created['id']}/links/confirm-all", headers=headers
    )
    film = next(s for s in created["suggestions"] if s["target"]["kind"] == "movie")

    response = stack.client.get(
        f"{API}/profiles/{pid}/items/{film['target']['qloo_id']}", headers=headers
    )

    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["title"] == "Interstellar" and detail["reason"] == "From your journal."
    assert detail["links"]
