# API contract

> **Pivot, 24 Oct 2026.** The old Phase 2 routes (sessions, shelf, warm-up, Person-mode signals, reactions) are removed. Phases 0 and 1 stay, with the small changes marked "Phase 2".

The backend's HTTP API. The backend owner leads this file and the frontend owner reviews it. Update it in the same PR as any endpoint change, then run `npm run gen:api` in `frontend/`.

## Conventions

- Every route lives under `/api/v1`. JSON uses snake_case.
- Every route except health sends `Authorization: Bearer <Supabase access token>`.
- Application errors return `{ "error": "<code>", "detail": "<message>" }`:

| Status | `error` | When |
|---|---|---|
| 404 | `not_found` | The resource doesn't exist, or belongs to someone else |
| 409 | `conflict` | The request doesn't fit the resource's state, such as confirming a link twice |
| 422 | `invalid_input` | The request is well-formed but breaks a rule |
| 429 | `rate_limited` | Too many requests of this kind, such as more than `FEED_RATE_LIMIT_PER_HOUR` feed builds in an hour |
| 502 | `upstream_error` | Qloo, YouTube, the LLM or speech to text failed or timed out |
| 500 | `internal_error` | Anything unexpected. Responses never include stack traces |

Unknown routes and request validation errors keep FastAPI's default shape: `{ "detail": ... }` only, where `detail` is a list for validation errors.

## Phase 0

### `GET /api/v1/health`

No auth. Response `200`:

```json
{ "status": "ok", "app_name": "MeloMind", "env": "development", "qloo_mode": "demo_fixtures" }
```

- `status`: always `"ok"`.
- `env`: the `APP_ENV` setting.
- `qloo_mode`: `"live"` when `QLOO_API_KEY` is set, otherwise `"demo_fixtures"`.

## Phase 1

Every route below needs `Authorization: Bearer <Supabase access token>`. A missing, expired or
invalid token returns `401` with `{ "error": "unauthorized", "detail": "..." }`. So does every
request when the backend has no `SUPABASE_URL`.

Profile-scoped routes check ownership: someone else's profile (or favourite) is a `404`
`not_found`, exactly like one that doesn't exist.

### Types

`Profile`:

```json
{
  "id": "uuid",
  "display_name": "Aanya",
  "birth_year": 2001,
  "country_code": "IN",
  "places_lived": ["Bangalore"],
  "languages": ["English", "Kannada"],
  "is_demo": true,
  "favourites": [Favourite]
}
```

- `display_name`: 1–60 characters, trimmed. Required.
- `birth_year`: 1900 to the current year. **Optional from Phase 2** (`null` when skipped); it only powers the `throwback` row.
- `country_code`: where they live, ISO 3166-1 alpha-2, upper-cased by the backend; or `null`.
- `places_lived`, `languages`: up to 10 strings of up to 100 characters. The first place is the
  hometown. Default `[]`.
- `favourites`: oldest first.

`Favourite`:

```json
{
  "id": "uuid",
  "name": "Glass Animals",
  "kind": "song",
  "qloo_id": "string or null",
  "verified": true,
  "song_title": "Heat Waves",
  "image_url": "string or null"
}
```

- `kind`: `artist`, `song`, `movie`, `tv_show` or `book`.
- `name`: for a song, the singer.
- `verified`: true when `qloo_id` is set, i.e. the user picked a taste-search match. Only
  verified favourites become Qloo signals.
- `song_title`: only for `kind: "song"`, otherwise `null`.
- `image_url` (Phase 2): the entity's image, or `null`.

### `POST /api/v1/demo/seed`

No body. `200`: `{ "profile_ids": ["uuid", "uuid"] }`. Creates the sample profiles for this user
the first time; later calls return the existing demo profile IDs and change nothing. Favourites
are resolved by name through taste search; any that don't match exactly, or if search fails,
are kept as text (`verified: false`).

### `GET /api/v1/profiles`

`200`: `Profile[]`, the user's profiles, oldest first.

### `POST /api/v1/profiles`

Body: `{ "display_name", "birth_year"?, "country_code"?, "places_lived"?, "languages"? }` (`birth_year` optional from Phase 2).
`201`: `Profile`. Validation failures are `422` with FastAPI's default shape.

### `GET /api/v1/profiles/{id}`

`200`: `Profile`. `404` if missing or not yours.

### `PATCH /api/v1/profiles/{id}`

Body: any profile fields. Fields left out are unchanged. `"country_code": null` clears it;
`"birth_year": null` clears it (Phase 2); `null` for `display_name`, `places_lived` or `languages` is a `422`. `200`: `Profile`.

### `DELETE /api/v1/profiles/{id}`

`204`. Deletes the profile and everything that belongs to it.

### `GET /api/v1/taste/search?q=&type=`

- `q`: 1–100 characters (blank after trimming is a `422`).
- `type` (optional): a favourite kind. `song` searches **artists**: search for the singer, never
  the song title. Without `type`, all four entity types are searched.

`200`: up to 8 matches:

```json
[{ "entity_id": "string", "name": "Arctic Monkeys", "type": "artist", "release_year": null, "image_url": "string or null" }]
```

- `type`: `artist`, `movie`, `tv_show` or `book`.
- `release_year`: release year for films and TV, publication year for books; `null` for artists.
- Results come from live Qloo or the demo fixtures; `GET /health`'s `qloo_mode` says which.
- `502` `upstream_error` if Qloo fails after retries.

### `POST /api/v1/profiles/{id}/favourites`

Body: `{ "name", "kind", "entity_id"?, "song_title"? }`.

- `name`: 1–120 characters. `entity_id`: the `entity_id` of the search match the user
  picked, or omitted to keep it as text. `song_title`: only with `kind: "song"`, else `422`.
- Saving the same favourite again returns the existing one.

`201`: `Favourite`.

### `DELETE /api/v1/profiles/{id}/favourites/{favourite_id}`

`204`. `404` if the favourite isn't on that profile.


## Phase 2: the feed

Every route needs `Authorization: Bearer <Supabase access token>` and checks ownership: someone
else's profile, feed, run or item is a `404`.

### Types

`FeedItem`:

```json
{
  "ref": "string",
  "title": "Arctic Monkeys",
  "entity_type": "artist",
  "year": null,
  "image_url": "https://… or null",
  "image_aspect": "square",
  "reason": "Because you liked The Strokes.",
  "because_of": { "ref": "string", "title": "The Strokes" },
  "affinity": 0.82,
  "popularity": 0.91,
  "tags": ["Indie rock", "Garage rock"],
  "description": "string or null",
  "source": "qloo_live",
  "links": [PlatformLink],
  "liked": false,
  "saved": false,
  "creator": null,
  "preview_url": null
}
```

- `ref`: the Qloo entity ID, `fav:<id>` for a favourite with none, or `song:<track id>` for a
  song card.
- `entity_type`: `artist`, `movie`, `tv_show`, `book` or `song`. Qloo's music picks are artists; a
  `song` is a top track of an artist Qloo picked, looked up in Apple's iTunes catalogue.
- `year`: release year for films, TV and songs, publication year for books, `null` for artists.
- `image_url`: Qloo's image, an Open Library cover for books, the iTunes artwork for songs, or
  `null` (show the fallback tile). `image_aspect`: `square` (artists, songs) or `poster` (films,
  TV, books).
- `source`: `qloo_live`, `demo_fixture`, `favourite` or `song_catalogue`. Show "Live Qloo", "Demo
  data" or "Song via iTunes".
- `creator`, `preview_url` (songs only, otherwise `null`): the credited artists, and Apple's
  30-second preview to stream on tap only, next to the Apple Music link, credited "courtesy of
  iTunes". Never download or cache it.
- A song's `because_of` is the signal behind its artist, and its `reason` names the artist
  ("A top song by Glass Animals, …").
- `tags`: up to 4 tag names, genres first, for chips.
- `because_of`: `{ ref, title }` of the signal behind the pick, or `null` (popular picks).
- `liked`, `saved`: the user's current state, for the heart and the bookmark.

`PlatformLink`:

```json
{ "platform": "netflix", "label": "Search on Netflix", "url": "https://…", "kind": "search" }
```

- `platform`: `youtube`, `spotify`, `youtube_music`, `apple_music`, `justwatch`, `netflix`,
  `prime_video`, `google_books`, `goodreads`, `amazon`, `open_library`, `imdb`.
- `kind`: `direct` (built from a Qloo external ID, or a song's Apple Music store link; label
  "Open on" / "Listen on") or `search` (label "Search on …"). The first link is the primary
  button. A song card's first link is "Listen on Apple Music".

`Feed`:

```json
{
  "id": "uuid",
  "profile_id": "uuid",
  "status": "done",
  "stale": false,
  "agent_run_id": "uuid",
  "summary": "More indie rock and sci-fi since yesterday.",
  "hero": FeedItem,
  "rows": [{ "key": "because_abc", "title": "Because you liked The Strokes", "subtitle": "Picked from what you play most", "placement": "main", "items": [FeedItem] }],
  "taste_tags": ["Indie", "Alternative", "Sci-fi"],
  "created_at": "2026-10-25T10:00:09Z"
}
```

- `placement`: `main` for the main column, `rail` for the right rail (`cross_culture`). The `cross_culture` row's title is "Cross-culture picks" and its subtitle "Because you like The 1975…".
- Row `key`s, in order when present: `for_you`, `cross_culture`, `because_<ref>` (up to 2),
  `music`, `songs` (song cards, right after `music`), `films`, `tv`, `books`, `new` ("New and
  notable"), `popular_<country>`, `throwback`. `journal` ("From your journal") comes right
  after the `because_` rows. Rows under 4 items are left
  out, so the frontend renders whatever arrives in order.
- `taste_tags`: up to 8 tag names for the sidebar's "Your taste profile" chips.

- `status`: `building`, `done` or `failed`.
- `stale`: true after feedback since this feed was built. Show "Refresh for new picks".
- An item appears at most once across `hero` and `rows`.

`AgentRun`:

```json
{
  "id": "uuid",
  "kind": "feed",
  "status": "running",
  "steps": [
    { "node": "research", "message": "Asked Qloo for films like The Strokes → 10 found.", "level": "info", "at": "…" }
  ],
  "result": null
}
```

- `kind`: `feed`, `resolve` or `link`. `status`: `running`, `done`, `failed` or `needs_hint`.
- Feed `node`s: `load_context`, `research`, `fallback`, `build_rows`, `add_songs`, `guardrails`,
  `decorate`, `explain`, and `feed` for the final line.
- `result` for `feed`: `{ "feed_id", "research_outcome", "fallback_attempts", "row_count", "item_count", "source" }`.

`ItemDetail`: a `FeedItem` plus
`{ "more_like_this": [FeedItem], "preview_available": true, "songs": [FeedItem] }`.

- `songs`: an artist's own top songs from the song catalogue (empty for other types, or with no
  catalogue).
- `preview_available`: whether `POST …/preview` can look up a YouTube video. A song plays its
  `preview_url` instead.

### `GET /api/v1/profiles/{id}/feed`

`200`: the latest `done` `Feed`. If none exists yet, `404` `not_found`: the frontend starts a build.

### `POST /api/v1/profiles/{id}/feed/refresh`

No body. `202`: `Feed` with `status: "building"` and its `agent_run_id`. Poll
`GET /agent-runs/{id}` once a second until `done` or `failed`, then `GET /feed`. If a build is
already running, returns that one. More than `FEED_RATE_LIMIT_PER_HOUR` builds in an hour is a `429`.

### `GET /api/v1/agent-runs/{id}`

`200`: `AgentRun`.

### `GET /api/v1/profiles/{id}/items/{ref}`

`200`: `ItemDetail`. `more_like_this` is up to 12 items from one insights call with this item as
the signal, minus exclusions (cached). For a song it's "After this song": Qloo's artists for the
song's artist, one top song each. `404` for an excluded item.

### `POST /api/v1/profiles/{id}/items/{ref}/preview`

No body. `200`: `{ "provider": "youtube", "video_id": "string", "title": "string", "duration_s": 212 }`,
or `404` when nothing playable was found (hide the button). Only when `YOUTUBE_API_KEY` is set;
otherwise `preview_available` is false and this is a `404`.

### `POST /api/v1/profiles/{id}/feedback`

Body: `{ "ref", "title", "entity_type"?, "signal", "platform"? }`, where `signal` is `liked`,
`unliked`, `saved`, `unsaved`, `opened`, `disliked` or `not_interested`. `quiz_pick` and
`journal_confirmed` are recorded by the app itself and are a `422` here.

`200`: `{ "ok": true, "counted": true, "effect": "Got it. You'll see fewer like this.", "stale": true }`.

- `not_interested` adds an exclusion and removes the item from the current feed snapshot at once.
- `opened` counts once per item per day (`counted: false` after that); `platform` is the link used.
  It doesn't mark the feed stale.
- `unliked` and `unsaved` undo their signal.
- On a song, `liked`, `unliked`, `saved`, `unsaved`, `opened` and `disliked` also count for its
  artist (Qloo has no songs to learn from). `not_interested` on a song hides only that song.

### `GET /api/v1/profiles/{id}/library`

`200`: `{ "liked": [FeedItem], "saved": [FeedItem] }`, newest first.

### `GET /api/v1/profiles/{id}/exclusions` · `DELETE …/exclusions/{exclusion_id}`

- `GET`: `200`, `[{ "id", "entity_ref", "title", "entity_type", "created_at" }]`, newest first.
- `DELETE`: undoes "not interested". `200`: the remaining list. Marks the feed stale.

### `POST /api/v1/profiles/{id}/quiz/next`

Body: `{ "picked_ref"?: "string", "shown_refs": ["string"] }`. Send every ref shown so far and the
one just picked. `200`: `{ "pair": [FeedItem, FeedItem], "round": 2, "rounds": 6, "done": false }`
or `{ "pair": null, "done": true }`.

- The set is about 16 popular, varied items for the profile's country (cached).
- After a pick, the pair is the unseen item most like it plus one of a different type.
- Each pick is a `quiz_pick` signal. `422` when `picked_ref` wasn't in the last pair.

## Phase 3: journal and taste page

### Types

`JournalEntry`:

```json
{
  "id": "uuid",
  "date": "2026-10-27",
  "text": "Rewatched Interstellar with my brother…",
  "mood": "nostalgic",
  "links": [JournalLink],
  "suggestions": [JournalLink],
  "link_run_id": "uuid or null",
  "created_at": "…",
  "updated_at": "…"
}
```

`JournalLink`:

```json
{
  "id": "uuid",
  "target": { "node_id": "uuid", "kind": "movie", "title": "Interstellar", "year": 2014, "qloo_id": "string or null", "creator": "string or null", "image_url": "string or null" },
  "kind": "mentions",
  "source": "agent",
  "status": "suggested",
  "reason": "You mentioned rewatching it."
}
```

- `links`: confirmed only. `suggestions`: `suggested` only. Rejected links are never returned.
- `target.kind`: `artist`, `song`, `movie`, `tv_show`, `book` or `place`. A song's `creator` is
  its artist, and its `qloo_id` is that artist's (Qloo has no songs).
- `link_run_id` is set only on the response that started a link run (create, a text change,
  suggest). Poll `GET /agent-runs/{id}` (kind `link`), then `GET` the entry. The run's `result`:
  `{ "entry_id", "suggested", "ai_read" }`; `ai_read: false` means the AI reader was off or
  failed, and only things you already love were spotted.

### `GET /api/v1/profiles/{id}/journal?from=&to=`

`200`: `JournalEntry[]`, newest first (default: the last 60 days).

### `POST /api/v1/profiles/{id}/journal`

Body: `{ "date"?, "text", "mood"? }`. `text`: 1–5,000 characters. `201`: `JournalEntry`, with
`link_run_id` set: the agent has started suggesting links. Poll the run, then `GET` the entry.

### `GET` · `PATCH` · `DELETE /api/v1/profiles/{id}/journal/{entry_id}`

- `GET`: `200`, `JournalEntry`.
- `PATCH`: body `{ "text"?, "mood"?, "date"? }`. Changing the text starts a new link run; confirmed
  links stay. `200`: `JournalEntry`.
- `DELETE`: `204`. Its links go too, and signals from them are removed.

### `POST /api/v1/profiles/{id}/journal/{entry_id}/links/suggest`

No body. `202`: `JournalEntry` with a new `link_run_id`: the agent suggests links again (after a
failed run, say). Earlier decisions stand: a rejected item is never suggested again.

### `POST /api/v1/profiles/{id}/journal/transcribe`

The raw recording as the body, with its `Content-Type`: `audio/webm`, `audio/ogg`, `audio/mp4`
or `audio/wav` (codec parameters such as `;codecs=opus` are fine), up to 2 minutes or 10 MB. Not
multipart, so the backend needs no form parser. `200`: `{ "text": "…" }`. The audio is
discarded. `422` for an unsupported, empty or too-long file; `502` if transcription fails or
isn't set up (no Groq key). The UI says "Couldn't hear that. Try again or type it".

### `PATCH /api/v1/profiles/{id}/journal/links/{link_id}`

Body: `{ "status": "confirmed" | "rejected" }`. `200`: `JournalLink`. Confirming a media link with
a Qloo ID adds a `journal_confirmed` signal and marks the feed stale. `409` if it's already decided.

### `POST /api/v1/profiles/{id}/journal/{entry_id}/links/confirm-all`

No body. `200`: `JournalEntry`.

### `GET /api/v1/profiles/{id}/taste`

`200`:

```json
{
  "sentence": "You love moody indie rock, big-idea sci-fi and character-driven drama.",
  "top_tags": [{ "name": "Indie rock", "weight": 0.9 }],
  "by_type": { "artist": 8, "movie": 5, "tv_show": 2, "book": 1 },
  "favourites": [Favourite],
  "recent_likes": [FeedItem]
}
```

### `GET /api/v1/profiles/{id}/taste/map`

`200`: `{ "nodes": [{ "id", "kind", "title", "image_url", "weight" }], "links": [{ "from", "to", "kind" }] }`.
Confirmed links only, at most `TASTE_MAP_MAX_NODES` nodes, most connected first.

### `POST /api/v1/profiles/{id}/favourites/resolve`

Body: `{ "text", "kind"?, "hint"? }`: `text` up to 300 characters (a name, a song, a lyric or a
description); `hint` up to 100 (singer, film or year) when re-running after a question. `202`:
`{ "agent_run_id" }`. The text is used for this run only and never stored or logged.

The run's `result`:
- `status: "done"`: `{ "proposals": [{ entity_id, name, type, kind, year, image_url, song_title, rung, why }] }`,
  up to 3. A song comes back as its singer with `kind: "song"` and the `song_title` (never a
  lyric). Confirm one by posting it to `/favourites` with `name`, `kind`, `entity_id`,
  `image_url` and `song_title`.
- `status: "needs_hint"`: `{ "proposals": [], "question": "Who sings it, or which film is it from?", "text_favourite": { name, kind, song_title } | null }`.
  Ask the question and re-run with `hint`, or save `text_favourite` as a text favourite (not a
  Qloo signal). `text_favourite` holds only names worked out, never what was typed.

## Phase 4: polish

### `POST /api/v1/profiles/{id}/ask`

Body: `{ "text"?: "Something like Interstellar but lighter", "mood"?: "chill" | "happy" | "focused" | "melancholy" | "energetic", "kind"?: "surprise" }` (text up to 300 characters; at least one field). The right rail's **Your vibe today** sends `mood`; **Surprise me** sends `kind: "surprise"` (lower affinity, high popularity, a type you use least). `202`:
`{ "agent_run_id" }`. The run's `result` is one extra row `{ "key": "ask", "title", "items" }`, shown
above the feed until dismissed. Same exclusions and guardrails as the feed.

### `POST /api/v1/profiles/{id}/taste-match`

Body: `{ "other_profile_id" }` (one of your profiles) or `{ "favourites": [entity_id] }` (up to 5).
`200`: `{ "shared_tags": [string], "score": 0.64, "row": { "key": "together", "title": "For you both", "items": [FeedItem] } }`.
Uses `compare`, then the shared tags as signals.
