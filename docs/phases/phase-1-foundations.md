# Phase 1: Foundations

**Dates:** Sat 24 Oct · **Hours:** about 7 each · **Previous:** [Phase 0](phase-0-setup.md) · **Next:** [Phase 2: Core loop](phase-2-core-loop.md)

**Goal:** a caregiver can try the demo, create a profile with just a name and birth year, and add favourites through Qloo search, all running locally. The Qloo adapter switches between fixtures and live.

**Before you start:** Phase 0's exit check has passed. Read `CLAUDE.md`, especially "Cold start" and "Qloo reference".

---

## First: agree the contract (all three, 30 minutes)

B writes it into `docs/API_CONTRACT.md`. Every route except health sends `Authorization: Bearer <token>`.

| Route | Request | Response |
|---|---|---|
| `POST /api/v1/demo/seed` | nothing | `{ profile_ids }`. Creates the sample profiles for this user once (idempotent) |
| `GET /api/v1/profiles` | nothing | `Profile[]` |
| `POST /api/v1/profiles` | `{ display_name, birth_year, country_code?, places_lived?, languages? }` | `Profile` |
| `GET /api/v1/profiles/{id}` | nothing | `Profile` |
| `PATCH /api/v1/profiles/{id}` | any profile fields | `Profile` |
| `DELETE /api/v1/profiles/{id}` | nothing | `204`. Deletes everything that belongs to the profile |
| `GET /api/v1/taste/search?q=&type=` | query string | `[{ entity_id, name, type, release_year }]` |
| `POST /api/v1/profiles/{id}/favourites` | `{ name, kind, entity_id?, song_title? }` | `Favourite`. `verified` is true when an `entity_id` was picked |
| `DELETE /api/v1/profiles/{id}/favourites/{fav_id}` | nothing | `204` |

`Profile` has these fields:
- `id`
- `display_name` (required)
- `birth_year` (required, 1920–1990)
- `country_code`: where they grew up, as an ISO 3166-1 alpha-2 code (optional). The Qloo adapter converts it to whatever `filter.release_country` expects.
- `places_lived` (optional)
- `languages` (optional)
- `is_demo`
- `favourites`

`Favourite` has these fields:
- `id`
- `name`
- `kind`: `artist`, `song`, `movie`, `tv_show` or `book`
- `qloo_id`
- `verified`
- `song_title`

---

## A: demo login, onboarding, favourites (≈ 7 h)

### A1. Try the demo
1. The button calls Supabase `signInAnonymously()` with the publishable key.
2. Then it calls `POST /demo/seed`.
3. Then it opens the profile list.

### A2. API client and shared states
- The API client attaches the token to every request.
- Add a shared error banner and empty states.

### A3. Onboarding (`/profiles/new`)

A stepper, one question per screen:
1. **Name and birth year** (required). Show: "A birth year is enough to start. You can add more any time."
2. **Where did they grow up?** A country, plus a town if known. "Not sure, skip".
3. **Languages** they enjoyed music or films in. "Not sure, skip".
4. **Favourites**, using the editor from A5. "Not sure, skip".

Step 1 creates the profile, and later steps update it, so a refresh never loses progress.

### A4. Profiles
- A list page.
- An edit page with the same fields as onboarding.

### A5. Favourites editor
- Search through `/taste/search`, debounced by 300 ms.
- Matches show type and year. A tap saves the favourite as verified.
- A "Not found? Keep it as text" option.
- For songs: search for the singer, then type the song title.

### A6. Book the caregiver conversation
- Find 1–3 real caregivers, care workers or music therapists.
- Book them to try the app on **Wed 28 Oct** (Phase 3).

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 1). Implement in frontend/src/features:
(1) demo: "Try the demo" button -> supabase.auth.signInAnonymously() -> POST
/demo/seed -> navigate to /profiles; (2) onboarding at /profiles/new: a stepper with
name + birth year (required; step 1 creates the profile), where they grew up
(country + optional town), languages, favourites; every optional step has a
"Not sure, skip" button and later steps PATCH the profile; (3) profiles: list page
and edit page; (4) favourites: editor with 300ms debounced search via /taste/search,
tap-to-verify, "keep it as text" fallback, song = singer search + song title.
Use the generated API types and TanStack Query. Loading, empty and error states,
phone layout, keyboard access. Run lint and build.
```

**Check:**
- Create a profile with only a name and birth year.
- Add 3 favourites through search, refresh, and everything is still there.
- It works at phone width.

---

## B: models, database, auth, profile APIs (≈ 7 h)

### B0. Supabase project (first hour, before A needs the demo login)
This is setup, not deployment. You use the project from localhost for all development.
- Create the project.
- Enable **anonymous sign-ins**.
- Make sure **asymmetric JWT signing keys** are on, and note the JWKS URL.
- Put `SUPABASE_URL` and `DATABASE_URL` in `backend/.env`, and give A the project URL and publishable key for `frontend/.env` (`VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY`).
- Keep the keys in a password manager. Never commit them.

### B1. Domain models
`domain/models.py` (C reviews): `Profile`, `Favourite` and their enums.

### B2. Persistence
- SQLAlchemy models and an Alembic migration for `profiles` and `favourites`.
- **RLS on, with no policies.**
- Deleting a profile deletes everything that belongs to it.
- Repositories: an in-memory version and a Postgres version.

### B3. Auth dependency
- Verify the token with PyJWT's `PyJWKClient` against the JWKS. Check `exp`, `iss` and `aud`.
- An `ensure_owner` helper that returns 404 for someone else's profile.

### B4. Routes
- Profiles and favourites.
- `demo/seed`:
  - uses C's fixture profiles;
  - adds their favourites by name, resolving each through `TasteService.search`, so the repo never holds real Qloo IDs.

### B5. Search route
Wire up `/taste/search` with C.

### B6. Tests
- Profile CRUD.
- Cross-user access returns 404.
- Validation: birth year required and within range.
- Deleting a profile deletes its favourites.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 1). Implement: domain models for
Profile and Favourite (dataclasses, no framework imports); repository ports;
in-memory and SQLAlchemy async repositories; an Alembic migration for profiles and
favourites with RLS enabled and no policies, and cascade deletes; a
get_current_user dependency verifying Supabase JWTs via PyJWKClient against
SUPABASE_URL's JWKS (check exp, iss, aud=authenticated); an ownership helper
returning 404 for other users; routes for profiles, favourites and demo/seed
(idempotent; seeds the fixture profiles and resolves their favourites by name via
TasteService.search). Tests: CRUD, cross-user 404, validation, cascade delete.
Run ruff and pytest.
```

**Check:** the endpoints appear in `/docs` on `localhost:8000`, CI is green, the API works from the frontend on `localhost:5173`, and the backend's Docker image still builds and serves `/api/v1/health` (with `--env-file backend/.env`).

---

## C: ports and the Qloo adapters (≈ 7 h)

### C1. Ports
`application/ports.py` (B reviews):
- `TasteGraph`, with `search` and `insights`;
- `EntityMatch`;
- `InsightsQuery`, including the age signal, country, popularity floor, exclusions, `take`, and a list of entities to score (for the warm-up in Phase 2);
- `MediaResolver`;
- `LanguageModel`;
- the repository protocols agreed with B.

### C2. `FixtureTasteGraph`
Search and insights over the fixtures, applying the type, year, exclusion and `take` filters.

### C3. `QlooHttpTasteGraph`
- httpx, the base URL and the `X-Api-Key` header.
- Maps `InsightsQuery` to GET parameters, allowing only supported ones.
- A 10-second timeout, with backoff retries on 429 and 5xx.
- Tolerant parsing.
- Tags results `source=qloo_live`.

### C4. `TasteService.search`
Add it, and the adapter choice in `deps.py` (with B).

### C5. Contract tests
Use `httpx.MockTransport` to test parameter building, parsing and retries.

### C6. When the key arrives
1. Run `scripts/qloo_smoke.py` locally.
2. Fix the parser to match the real response shapes.
3. Work through the "To verify" list in `QLOO_NOTES.md`.
4. Check coverage for older Western and Indian titles, and record it. This decides whether Lakshmi stays in the demo.

**Prompt for Claude Code:**
```
Read CLAUDE.md, docs/QLOO_NOTES.md and docs/AGENT.md. Implement application/ports.py
(TasteGraph with search and insights, EntityMatch, InsightsQuery with age signal,
country, popularity floor, exclusions, take and an optional list of entities to
score, MediaResolver, LanguageModel, repository protocols agreed with B).
Implement infrastructure/qloo: FixtureTasteGraph over the hand-written fixtures
(apply type, year range, exclusions, take) and QlooHttpTasteGraph (httpx async,
X-Api-Key header, GET params from InsightsQuery with only supported params, 10s
timeout, retry with backoff on 429/5xx, tolerant parsing). Add TasteService.search.
Contract tests with httpx.MockTransport for param building, parsing and retries.
No live calls in tests. Run ruff and pytest.
```

**Check:** search works on fixtures (and live, once the key is in), and insights returns candidates for both sample profiles.

---

## Exit check

Locally (frontend on `localhost:5173`, backend on `localhost:8000`, and once with the backend in Docker):
- **Try the demo** shows the sample profiles.
- A profile created with only a name and birth year saves.
- 3 favourites added through search survive a refresh.
- It works at phone width (browser device mode, or a phone on your local network).
- Setting `QLOO_API_KEY` switches the adapter to live Qloo, and the health check says so.

## If you're behind

- **Cut first:** the languages step (keep the field in the API).
- **Never cut:** demo login and the ownership checks.
