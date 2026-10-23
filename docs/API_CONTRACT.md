# API contract

The backend's HTTP API. The backend owner leads this file and the frontend owner reviews it. Update it in the same PR as any endpoint change, then run `npm run gen:api` in `frontend/`.

## Conventions

- Every route lives under `/api/v1`. JSON uses snake_case.
- Every route except health sends `Authorization: Bearer <Supabase access token>`.
- Application errors return `{ "error": "<code>", "detail": "<message>" }`:

| Status | `error` | When |
|---|---|---|
| 404 | `not_found` | The resource doesn't exist, or belongs to someone else |
| 409 | `conflict` | The request doesn't fit the resource's state, such as approving a session twice |
| 422 | `invalid_input` | The request is well-formed but breaks a rule |
| 429 | `rate_limited` | Too many requests of this kind, such as more than 10 plans in an hour |
| 502 | `upstream_error` | Qloo, YouTube or the LLM failed or timed out |
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
  "display_name": "Margaret",
  "birth_year": 1948,
  "country_code": "US",
  "places_lived": ["Chicago, Illinois"],
  "languages": ["English"],
  "is_demo": true,
  "favourites": [Favourite]
}
```

- `display_name`: 1–60 characters, trimmed. Required.
- `birth_year`: 1920–1990. Required.
- `country_code`: where they grew up, ISO 3166-1 alpha-2, upper-cased by the backend; or `null`.
- `places_lived`, `languages`: up to 10 strings of up to 100 characters. The first place is the
  hometown. Default `[]`.
- `favourites`: oldest first.

`Favourite`:

```json
{
  "id": "uuid",
  "name": "The Temptations",
  "kind": "song",
  "qloo_id": "string or null",
  "verified": true,
  "song_title": "My Girl"
}
```

- `kind`: `artist`, `song`, `movie`, `tv_show` or `book`.
- `name`: for a song, the singer.
- `verified`: true when `qloo_id` is set, i.e. the caregiver picked a taste-search match. Only
  verified favourites become Qloo signals.
- `song_title`: only for `kind: "song"`, otherwise `null`.

### `POST /api/v1/demo/seed`

No body. `200`: `{ "profile_ids": ["uuid", "uuid"] }`. Creates the sample profiles for this user
the first time; later calls return the existing demo profile IDs and change nothing. Favourites
are resolved by name through taste search; any that don't match exactly, or if search fails,
are kept as text (`verified: false`).

### `GET /api/v1/profiles`

`200`: `Profile[]`, the user's profiles, oldest first.

### `POST /api/v1/profiles`

Body: `{ "display_name", "birth_year", "country_code"?, "places_lived"?, "languages"? }`.
`201`: `Profile`. Validation failures are `422` with FastAPI's default shape.

### `GET /api/v1/profiles/{id}`

`200`: `Profile`. `404` if missing or not yours.

### `PATCH /api/v1/profiles/{id}`

Body: any profile fields. Fields left out are unchanged. `"country_code": null` clears it;
`null` for `display_name`, `birth_year`, `places_lived` or `languages` is a `422`. `200`: `Profile`.

### `DELETE /api/v1/profiles/{id}`

`204`. Deletes the profile and everything that belongs to it.

### `GET /api/v1/taste/search?q=&type=`

- `q`: 1–100 characters (blank after trimming is a `422`).
- `type` (optional): a favourite kind. `song` searches **artists**: search for the singer, never
  the song title. Without `type`, all four entity types are searched.

`200`: up to 8 matches:

```json
[{ "entity_id": "string", "name": "The Supremes", "type": "artist", "release_year": null }]
```

- `type`: `artist`, `movie`, `tv_show` or `book`.
- `release_year`: release year for films and TV, publication year for books; `null` for artists.
- Results come from live Qloo or the demo fixtures; `GET /health`'s `qloo_mode` says which.
- `502` `upstream_error` if Qloo fails after retries.

### `POST /api/v1/profiles/{id}/favourites`

Body: `{ "name", "kind", "entity_id"?, "song_title"? }`.

- `name`: 1–120 characters. `entity_id`: the `entity_id` of the search match the caregiver
  picked, or omitted to keep it as text. `song_title`: only with `kind: "song"`, else `422`.
- Saving the same favourite again returns the existing one.

`201`: `Favourite`.

### `DELETE /api/v1/profiles/{id}/favourites/{favourite_id}`

`204`. `404` if the favourite isn't on that profile.

## Phase 2

Every route needs `Authorization: Bearer <Supabase access token>` and checks ownership: someone
else's profile, session, run or item is a `404`.

### Types

`SessionDraft` (a session or a warm-up set):

```json
{
  "id": "uuid",
  "profile_id": "uuid",
  "status": "draft",
  "mode": "standard",
  "target_minutes": 20,
  "total_duration_s": 1180,
  "agent_run_id": "uuid",
  "items": [SessionItem],
  "created_at": "2026-10-25T10:00:00Z",
  "updated_at": "2026-10-25T10:00:09Z"
}
```

- `status`: `planning` → `draft` → `approved` → `in_progress` → `completed`, or `planning` →
  `failed`. A warm-up set (`mode: "warmup"`) stops at `approved`.
- `mode`: `standard` or `warmup`.
- `items`: in play order.

`SessionItem`:

```json
{
  "id": "uuid",
  "position": 0,
  "ref": "string",
  "title": "The Four Tops",
  "entity_type": "artist",
  "release_year": 1964,
  "age_at_release": 16,
  "reason": "Similar to The Supremes, which Margaret loves.",
  "prompt": "What does this music bring to mind?",
  "source": "qloo_live",
  "media": { "provider": "youtube", "ref": "videoId", "duration_s": 182, "title": "string" },
  "duration_s": 182
}
```

- `ref`: the Qloo entity ID, or `fav:<id>` for a favourite with none.
- `entity_type`: `artist`, `movie`, `tv_show` or `book`. `release_year` is `null` for artists
  from live Qloo, and `age_at_release` is `null` when the year is unknown.
- `source`: `qloo_live`, `demo_fixture` or `favourite`. Show "Live Qloo" or "Demo data".
- `media`: `null` for a **book**, which is a 3-minute conversation slot (`duration_s: 180`).
  `provider` is `youtube`, or `demo` for stand-in media when `YOUTUBE_API_KEY` is empty.
- `prompt`: for the caregiver only. `null` in a warm-up set.

`ShelfItem` (Person mode). It never has a reason or a prompt:

```json
{
  "ref": "string",
  "title": "My Girl",
  "entity_type": "song",
  "release_year": null,
  "decade": null,
  "media": { "provider": "youtube", "ref": "videoId", "duration_s": 165, "title": "string" },
  "from": "favourite"
}
```

- `entity_type`: `artist`, `song`, `movie` or `tv_show` (the card's icon). Books never appear.
- `release_year` and `decade` are `null` for favourites, whose year isn't stored.
- `from`: `favourite`, `session` or `warmup`. Each `ref` appears once.

`AgentRun`:

```json
{
  "id": "uuid",
  "kind": "plan",
  "status": "running",
  "steps": [
    { "node": "research", "message": "Asked Qloo for films… → 9 found.", "level": "info", "at": "…" }
  ],
  "result": null
}
```

- `kind`: `plan` (later also `resolve` and `link`). `status`: `running`, `done` or `failed`.
- `level`: `info`, or `warning` when something went wrong and the agent recovered.
- `result`: once finished, `{ "session_id", "research_outcome", "fallback_attempts",
  "item_count", "total_duration_s", "source" }` (only `session_id` when it failed).

`Feedback` answer: `{ "ok": true, "counted": true, "effect": "Rejected. It won't be suggested
again." }`. `counted` is false when a signal was ignored: a skip after 15 seconds or more, or the
same signal for the same item again that day.

`Exclusion`: `{ "id", "entity_ref", "title", "reason": "rejected" | "upset", "needs_review",
"created_at" }`. `needs_review` is true for a hidden (`upset`) item nobody has reviewed yet.

### `POST /api/v1/profiles/{id}/sessions/plan`

Body: `{ "mode": "standard" | "warmup", "target_minutes": 10 | 20 | 30, "instructions"? }`.
Defaults: `standard`, 20. `instructions` (up to 500 characters) is accepted and ignored until
Phase 4. Unknown modes and other lengths are a `422`.

`202`: `SessionDraft` with `status: "planning"` and its `agent_run_id`. The agent runs in the
background; poll `GET /agent-runs/{id}` once a second until `done` or `failed`, then
`GET /sessions/{id}`. More than 10 plans in an hour is a `429` (the demo seed's warm-up plans
don't count).

### `GET /api/v1/sessions/{id}`

`200`: `SessionDraft`.

### `GET /api/v1/agent-runs/{id}`

`200`: `AgentRun`.

### `PATCH /api/v1/sessions/{id}/items`

Body: `{ "removed"?: [item_id], "order"?: [item_id], "prompts"?: { "<item_id>": "text" } }`.
Removals apply first; `order` must then list every remaining item once. Prompts are trimmed to
300 characters, and an empty prompt clears it. A warm-up set has no prompts.

`200`: `SessionDraft`. `409` unless the session is a `draft`. `422` for unknown item IDs or a bad
order.

### `POST /api/v1/sessions/{id}/approve` · `/start` · `/complete`

No body. `200`: `SessionDraft`. `409` for any change the status machine doesn't allow, including
starting a warm-up set. Approving a draft with no items is a `422`.

### `POST /api/v1/sessions/{id}/items/{item_id}/feedback`

Body: `{ "reaction": "sang_along" | "smiled" | "calm" | "neutral" | "upset" | "rejected",
"note"? }`. `200`: `Feedback`.

- `rejected` adds an exclusion: the item never appears again, anywhere.
- `upset` hides the item and queues it for review (`needs_review: true`).
- `409` while the session is `planning` or `failed`.

### `GET /api/v1/profiles/{id}/history`

`200`: `[{ "id", "mode", "status", "item_count", "total_duration_s", "created_at" }]`, newest
first, including warm-up sets.

### `GET /api/v1/profiles/{id}/shelf`

`200`: `ShelfItem[]`: verified favourites with a playable video, then the latest approved warm-up
set, then items from approved sessions. Only playable items; never excluded or hidden ones.

### `POST /api/v1/profiles/{id}/warmup/next`

Body: `{ "chosen_ref"?: "string", "shown_refs": ["string"] }`. Send every ref shown so far, and
the one just tapped. `200`: `{ "pair": [ShelfItem, ShelfItem], "done": false }` or
`{ "pair": null, "done": true }`.

- Pairs come from the latest approved warm-up set. The first pair differs in type or decade.
  After a tap, the pair is the unseen item most like the chosen one, plus one different item.
- Each tap is stored as a `chose` signal. It ends after `WARMUP_PAIRS` pairs or when the set runs
  out. `409` when there's no approved warm-up set; `422` when `chosen_ref` isn't in it.

### `POST /api/v1/profiles/{id}/person-signals`

Body: `{ "item_ref", "signal": "chose" | "loved" | "replayed" | "skipped", "played_s"? }`.
`200`: `Feedback`. The item must be on the shelf (`422` otherwise). A skip counts only when
`played_s` is under 15. Each signal counts once per item per day.

### `POST /api/v1/profiles/{id}/reactions`

The caregiver button inside Person mode. Body: `{ "item_ref", "reaction", "note"? }`, with the
same reactions and effects as the session item route. `200`: `Feedback`. `404` for a ref that
isn't a favourite or an item of this profile's sessions.

### `GET` · `POST /api/v1/profiles/{id}/exclusions` · `DELETE …/exclusions/{exclusion_id}`

- `GET`: `200`, `Exclusion[]`, oldest first.
- `POST`: body `{ "entity_ref", "title", "reason": "rejected" | "upset" }`. `201`: every
  `Exclusion`. There is one per ref: a rejection stays a rejection, and a hidden item can be
  upgraded to rejected.
- `DELETE`: lets a hidden item back in after review. `200`: the remaining `Exclusion[]`. A
  rejection is for good: deleting one is a `409`.
