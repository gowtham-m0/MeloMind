# Phase 3: Journal and taste page

**Dates:** Tue 27 – Wed 28 Oct · **Hours:** about 10 each · **Previous:** [Phase 2](phase-2-core-loop.md) · **Next:** [Phase 4: Polish and freeze](phase-4-bridge-and-freeze.md)

**Goal:** the signature feature works locally.
- You write or **speak** a journal entry. The agent suggests the artists, films, shows and books you mentioned, and you confirm them.
- Confirmed items shape the feed: a **From your journal** row appears.
- The **taste page** shows your taste in a sentence, top tags, your favourites and likes, and the **taste map**.
- The favourite resolver ("Type a line you remember") arrives too, because journal linking reuses its hint ladder.

**Before you start:** Phase 2's exit check has passed. Read `CLAUDE.md`: "Journal", "Taste page", "Workflow 2", "Workflow 3" and rule 11.

> This file replaces the old Memory Graph phase. What carries over: the suggested → confirmed → rejected link model, "a rejected suggestion is never suggested again", the hint ladder, the privacy rules, and a capped graph view (now the taste map). What's dropped: people and decade nodes, "Use in prompts", conversation prompts, the `[[` picker.

---

## First: agree the contract (all three, 30 minutes, Tuesday at the start of the evening)

The full shapes are in `docs/API_CONTRACT.md`, "Phase 3: journal and taste page".

| Route | Request | Response |
|---|---|---|
| `GET /api/v1/profiles/{id}/journal?from=&to=` | query string | `JournalEntry[]` |
| `POST /api/v1/profiles/{id}/journal` | `{ date?, text, mood? }` | `JournalEntry` with `link_run_id` |
| `GET` / `PATCH` / `DELETE /api/v1/profiles/{id}/journal/{entry_id}` | — | `JournalEntry` / `204` |
| `POST /api/v1/profiles/{id}/journal/transcribe` | `multipart: audio` | `{ text }` |
| `PATCH /api/v1/profiles/{id}/journal/links/{link_id}` | `{ status: confirmed \| rejected }` | `JournalLink` |
| `POST /api/v1/profiles/{id}/journal/{entry_id}/links/confirm-all` | nothing | `JournalEntry` |
| `GET /api/v1/profiles/{id}/taste` | nothing | `{ sentence, top_tags, by_type, favourites, recent_likes }` |
| `GET /api/v1/profiles/{id}/taste/map` | nothing | `{ nodes, links }` |
| `POST /api/v1/profiles/{id}/favourites/resolve` | `{ text, kind? }` | `{ agent_run_id }` |

---

## Agent: resolver, journal linking, speech, taste sentence (≈ 10 h)

### Agent 1. The `resolve_favourite` workflow
- It climbs the hint ladder from `CLAUDE.md`, logging each rung.
- At most `RESOLVE_MAX_SEARCHES` (5) searches.
- It checks type, year and name before accepting a match.
- It returns up to 3 proposals with images.

### Agent 2. The `find_journal_links` tool
A thin wrapper over the journal repository port, scoped to the profile. It includes rejected links, so rejected suggestions can be recognised.

### Agent 3. The `link_journal` workflow (`docs/AGENT.md`, section 5)
1. **Extract mentions** with structured output, Groq only: artists, songs, films, TV shows, books, places and a mood. Never people's names.
2. **Resolve the media mentions** with the hint ladder, within `LINK_MAX_SEARCHES` (10) in total.
3. **Match** places and earlier items to existing nodes with `find_journal_links`; propose new nodes otherwise.
4. **Skip anything already rejected** for this profile.
5. **Save the suggestions** with `propose_links`, each with a short reason ("You mentioned rewatching it").

### Agent 4. Speech to text
- A `SpeechToText` port and a Groq Whisper adapter (`STT_MODEL`, the Groq key), with a fake for tests.
- Limits: 2 minutes or 10 MB; webm, ogg, mp4 or wav. The audio is never written to disk or logged.

### Agent 5. The `journal` row and the taste sentence
- The `journal` row strategy: `applies` when there's at least one confirmed media link; one `get_insights` with those items as signals.
- `TasteProfileService.sentence`: one LLM call from tag names and titles only, with a template fallback ("You love indie rock, sci-fi films and literary fiction").

### Agent 6. Demo journal
For each demo profile, 3–4 hand-written entries with confirmed links, all `"demo": true`.

### Agent 7. Tests
- **Journal text never reaches the Qloo adapter** (use a spy adapter).
- The ladder stops at 5 searches, and a link run stops at 10.
- Suggested links don't affect the feed or the taste page.
- A rejected suggestion isn't proposed again.
- Transcription failure returns an error, and nothing is stored.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Journal", "Workflow 2", "Workflow 3", rule 11) and docs/AGENT.md
(sections 4, 5, 12). Build workflows/resolve_favourite.py (the hint ladder, max
RESOLVE_MAX_SEARCHES, accept a match only after checking type, year and name, up to
3 proposals with images, every rung logged) and workflows/link_journal.py (Groq-only
structured extraction of artists, songs, films, TV shows, books, places and mood, never
people; resolve media with the hint ladder within LINK_MAX_SEARCHES; match places and
earlier items with a new find_journal_links tool; skip rejected links; save
suggestions via propose_links with a reason). Add a SpeechToText port with a Groq
Whisper adapter and a fake. Add the journal row strategy and a taste sentence with a
template fallback. Tests: journal text never reaches the Qloo adapter (spy), search
limits, suggested links have no effect, rejected suggestions are not re-proposed,
transcription failure stores nothing. Run ruff and pytest.
```

**Check:** the entry "Rewatched Interstellar with my brother, then had Glass Animals on repeat" gets Interstellar (film) and Glass Animals (artist) as suggestions, and no person.

---

## Backend: journal storage, signals, taste page, routes (≈ 10 h)

### Backend 1. Migration and repositories
- `journal_nodes` (`id`, `profile_id`, `kind`: `entry`, `artist`, `song`, `movie`, `tv_show`, `book`, `place`; `title`, `body` for entries, `date`, `mood`, `year`, `qloo_id`, `image_url`, `created_at`) and `journal_links` (`id`, `profile_id`, `from_id`, `to_id`, `kind`, `source`, `status`, `reason`), with RLS on.
- A unique key on `(from_id, to_id, kind)`.
- In-memory and Postgres repositories.

### Backend 2. `JournalService`
- Create, edit and delete entries. Saving or changing the text starts a `link` run.
- Confirm or reject suggestions; "confirm all".
- **On confirm** of a media node with a Qloo ID: a `journal_confirmed` signal (+1.0) and the feed marked stale.
- Deleting an entry deletes its links and removes the signals that came only from them.
- Deleting a profile deletes its journal.

### Backend 3. Transcribe route
`POST /journal/transcribe`: validate type and size, call the `SpeechToText` port, return the text. Never store the audio.

### Backend 4. `TasteProfileService`
- `taste()`: the sentence, top tags (counted from the tags on favourites and strong signals), counts by type, favourites, recent likes.
- `taste_map()`: favourites, strong signals and confirmed journal items as nodes; `because_of` links from feed items the user liked to the signal behind them, and `mentions` links from entries; capped at `TASTE_MAP_MAX_NODES` (most connected, then most recent).
- Feed items keep `because_of` so these links exist.

### Backend 5. Routes and resolver run
- The whole contract, with ownership checks.
- `journal` saves and `favourites/resolve` start agent runs (kinds `link` and `resolve`), polled like feed builds.

### Backend 6. Demo seed
Add the agent's demo journal entries and links; resolve their media nodes by name through `TasteService.search`.

### Backend 7. Tests
- Cross-user access is denied.
- Confirming a link adds the signal and marks the feed stale; rejecting adds nothing.
- A rejected link stays rejected.
- The taste map respects its cap and shows confirmed links only.
- Deleting an entry or a profile deletes its journal.
- Transcribe rejects bad files and stores nothing.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Journal", "Taste page", rule 11) and docs/API_CONTRACT.md (Phase 3).
Add journal_nodes and journal_links (RLS on, unique from/to/kind) with an Alembic
migration and in-memory + Postgres repositories. Implement JournalService (entry CRUD,
start a link run on save or text change, confirm/reject/confirm-all, a
journal_confirmed signal and stale feed on confirming a media node with a Qloo ID,
cascade deletes), the transcribe route (validate, call SpeechToText, never store
audio), and TasteProfileService (taste sentence, top tags, counts, favourites, recent
likes; a capped taste map of confirmed links only). All Phase 3 routes with ownership
checks; journal saves and favourites/resolve start agent runs. Seed the demo journal.
Tests: cross-user 404, confirm adds a signal, reject adds nothing, rejected stays
rejected, map cap, cascade deletes, transcribe validation. Run ruff and pytest.
```

**Check:** every Phase 3 route works in `/docs` against the seeded demo journals.

---

## Frontend: journal, voice, taste page, taste map, the lyric box (≈ 10 h)

Use the design skills as in Phase 2: `/impeccable shape` first, `animate` for motion, `critique`, `audit`, `polish`, `review-animations` and `break-ui` before each PR.

### Frontend 1. Pick the taste map library (first hour)
- Try react-force-graph and Cytoscape.js against the map response.
- Pick one, and tell the team (`CLAUDE.md`, rule 15).

### Frontend 2. Journal page (`/journal`)
- A composer at the top: date, a calm text area, mood chips, and a large **mic button**.
- Voice: tap to record (`MediaRecorder`), a live timer and level meter, tap to stop; the transcript appears in the text area for editing before saving. Clear permission and error states ("Couldn't hear that. Try again or type it").
- The privacy note: "Your journal is private. It's never shared."
- The timeline: entries by day, each with its confirmed items as small thumbnails.

### Frontend 3. Suggestions
- After saving, the link run is polled, with a compact live log.
- Suggestions appear as image chips ("Interstellar · film") with ✓ and ✗, plus "Confirm all". Confirmed chips settle into the entry with a small motion.
- A toast: "Added to your taste. Refresh your feed to see it."

### Frontend 4. Taste page (`/taste`)
- The taste sentence as a large Chillax headline.
- Top tags as weighted chips; counts by type as a small, tasteful bar.
- Favourites and recent likes as an image grid, with remove and undo.
- The **taste map**: nodes as round thumbnails coloured by type, `because_of` and `mentions` links, tap to open the detail sheet; a list view toggle that always works; an empty state that suggests liking a few things.

### Frontend 5. "Type a line you remember" (in onboarding favourites and the taste page)
1. Sends the text to `favourites/resolve` and polls the run.
2. Shows up to 3 proposals with images, type and year.
3. Tap one to confirm, or add a hint (singer, film or year) to run it again.
4. The box clears afterwards. The lyric is never shown again or saved.

### Frontend 6. Feed and rail
- The **From your journal** row on the feed.
- Quick action "Write in your journal" in the right rail opens the composer.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Journal", "Taste page", "Design system", "Frontend conventions") and
docs/API_CONTRACT.md (Phase 3). Use the impeccable and animate skills. Build
features/journal: a composer (date, text, mood chips, a mic button that records with
MediaRecorder, shows a timer and level, and puts the transcript in the text area for
editing; privacy note), a timeline by day with confirmed item thumbnails, and a
suggestions area that polls the link run, shows its log, and offers image chips with
confirm/reject and "Confirm all". Build features/taste: the taste sentence, weighted
tag chips, counts by type, a favourites and likes grid with undo, and the taste map
with <chosen library> (round thumbnails coloured by type, tap opens the detail sheet,
list view toggle, empty state). Add "Type a line you remember" to favourites: post to
/favourites/resolve, poll, show up to 3 proposals, confirm or add a hint, clear
afterwards. Add the journal row and the rail quick action. Designed states, phone
layout, keyboard access. Run lint and build.
```

**Check:** speak an entry, confirm its links, and see them on the taste map and (after a refresh) in the feed, on a phone and a laptop.

---

## Exit check (Wednesday night)

Locally:
1. Open Aanya's journal. The seeded entries show with their items.
2. Speak "Rewatched Interstellar with my brother, then had Glass Animals on repeat", edit the transcript if needed, save, and confirm the suggested links.
3. Refresh the feed. **From your journal** appears.
4. Open the taste page. The sentence, tags and taste map include the new items.
5. Reject a suggestion on another entry, edit that entry's text, and check it isn't suggested again.

## If you're behind

- **Cut first:** the taste map (keep the list and the grid).
- **Then cut:** voice (keep typing), then "Type a line you remember".
- **If it still isn't done by Wednesday night:** use Thursday morning to finish typed entries and confirmed links, and cut Phase 4's extras.
- **Never cut:** user confirmation of links, the privacy rules, rejected suggestions staying rejected.
