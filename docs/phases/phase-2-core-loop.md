# Phase 2: Core loop

**Dates:** Sun 25 – Mon 26 Oct · **Hours:** about 15 each · **Previous:** [Phase 1](phase-1-foundations.md) · **Next:** [Phase 3: Memory Graph](phase-3-memory-graph.md)

**Goal:** the whole product loop works locally.
- The agent plans a session.
- The caregiver reviews and approves it.
- The caregiver plays it and records reactions.
- The person chooses in Person mode.
- The next plan changes because of all of it.

**Before you start:** Phase 1's exit check has passed. Read `CLAUDE.md`, especially "The agent", "Session modes", "Cold start", "Person mode" and "Learning rules".

**This is the key milestone.** Everything after it is an addition.

---

## First: agree the contract (all three, 30 minutes, Sunday 10 AM)

| Route | Request | Response |
|---|---|---|
| `POST /api/v1/profiles/{id}/sessions/plan` | `{ mode: "standard" \| "warmup", target_minutes: 10 \| 20 \| 30, instructions? }` | `SessionDraft` with status `planning` and an `agent_run_id` |
| `GET /api/v1/sessions/{id}` | nothing | `SessionDraft` |
| `GET /api/v1/agent-runs/{id}` | nothing | `{ id, kind: plan \| resolve \| link, status: running \| done \| failed, steps: [{ node, message, at }], result? }` |
| `PATCH /api/v1/sessions/{id}/items` | `{ order?: item_id[], removed?: item_id[], prompts?: { item_id: text } }` | `SessionDraft` |
| `POST /api/v1/sessions/{id}/approve` · `/start` · `/complete` | nothing | `SessionDraft` |
| `POST /api/v1/sessions/{id}/items/{item_id}/feedback` | `{ reaction, note? }` | `{ ok, effect }` |
| `GET /api/v1/profiles/{id}/shelf` | nothing | `ShelfItem[]` |
| `POST /api/v1/profiles/{id}/warmup/next` | `{ chosen_ref?, shown_refs: [] }` | `{ pair: [ShelfItem, ShelfItem] }` or `{ done: true }`. `409` if there's no approved warm-up set |
| `POST /api/v1/profiles/{id}/person-signals` | `{ item_ref, signal, played_s? }` | `{ ok, effect }` |
| `GET` / `POST` / `DELETE /api/v1/profiles/{id}/exclusions` | — / `{ entity_ref, reason }` / — | `Exclusion[]` |
| `GET /api/v1/profiles/{id}/history` | nothing | `SessionSummary[]` |

**`SessionDraft`** has these fields:
- `id`
- `status`: `planning`, `draft`, `approved`, `in_progress`, `completed` or `failed`
- `mode`
- `total_duration_s`
- `agent_run_id`
- `items`

**Status changes:** `planning` → `draft` → `approved` → `in_progress` → `completed`, or `planning` → `failed`. A warm-up set stops at `approved`.

**Each item** has these fields:
- `id`
- `position`
- `ref`
- `title`
- `entity_type`
- `release_year`
- `age_at_release`
- `reason`
- `prompt`
- `source`
- `media`: `{ provider, ref, duration_s }` or `null`

**`ShelfItem`** has these fields:
- `ref`
- `title`
- `entity_type`
- `release_year`
- `decade`
- `media`
- `from`: `favourite`, `session` or `warmup`

There are no prompts or reasons on shelf items. Person mode never shows them.

**`ref`** is a stable reference: the Qloo entity ID when there is one, otherwise `fav:<id>`.

**Reactions** (caregiver): `sang_along`, `smiled`, `calm`, `neutral`, `upset`, `rejected`.

**Signals** (person): `chose`, `loved`, `replayed`, `skipped`. A skip counts only when `played_s` is under 15.

**Other notes**
- `instructions` is accepted now but ignored until Phase 4.
- Agent-run steps include the research agent's tool calls, shown as steps from the `research` node.

---

## Agent: the agent (≈ 15 h)

### Agent 1. Stub planner (Sunday by 11 AM)
It returns a fixed `SessionDraft` in the real shape, for both `standard` and `warmup`, so the frontend and backend can build against it.

### Agent 2. Tools
In `application/agent/tools/`, each logging its call:
- `search_entities`;
- `find_tags`;
- `get_insights`, which adds the profile's exclusions itself and allows only supported parameters;
- `submit_candidates`.

### Agent 3. The research agent
Built with `create_agent`:
- a system prompt built from the mode's research brief;
- middleware limits:
  - `ToolCallLimitMiddleware` (12 Qloo calls);
  - `ModelCallLimitMiddleware` (8);
  - `ToolRetryMiddleware`;
  - `ModelFallbackMiddleware`;
- a 25-second timeout.

### Agent 4. The `plan_session` workflow
The outer LangGraph graph:
1. `load_context`
2. `research`
3. `fallback` (only when needed)
4. `select_items`
5. `resolve_media`
6. `guardrails`
7. `compose`

### Agent 5. `StandardMode` and `ModeRegistry`
- **The research brief**, with the three cold-start tiers from `CLAUDE.md`:
  - 3 or more favourites;
  - 1–2 favourites or a hint;
  - nothing specific.
- **The fallback queries:**
  - the era window and popularity floor;
  - a mix of 4 artists, 2 films, 1 TV show and 1 book.
- **Selection,** with spares.

### Agent 6. `WarmupMode`
- About 12 varied, well-known, playable items, across types and decades within their era.
- A high popularity floor.
- No prompts, because Person mode never shows them, so `compose` skips the LLM for this mode.

### Agent 7. Set scoring for the warm-up
- Add `TasteService.score(candidates, signal)`. It asks Qloo Insights with the chosen item as the signal and `filter.results.entities` set to the candidates.
- If that isn't supported, it falls back to the same type and the closest year.
- It logs which path ran. The backend's warm-up service calls it.

### Agent 8. LLM adapter
Structured output, plus the **template fallback** for reasons and prompts.
- `infrastructure/llm/factory.py` builds a chat model for `groq` or `gemini`; `deps.py` wires Groq as the main model and Gemini as the fallback.
- An 8-second timeout on each Groq call, then one try on Gemini, then the templates.
- `link_memory` stays on Groq only (memory notes never go to a free Gemini key).
- Add `langchain-groq` and `langchain-google-genai` with exact pins.

### Agent 9. Media resolver
- YouTube search, then `videos.list` to check `embeddable` and read the duration.
- Cached through the backend's `media_cache`.
- A demo resolver for fixture mode.

### Agent 10. Tests
Use a scripted fake chat model:
- an empty search leads to the next hint;
- hitting a limit triggers the fallback;
- `get_insights` always adds the exclusions;
- blocked items never pass the guardrails;
- every item has a source;
- duration is within ±10 %;
- the template fallback runs when the LLM fails;
- each cold-start tier builds the right brief;
- set scoring falls back when Qloo returns nothing.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/AGENT.md. Build the hybrid agent in application/agent:
tools/ (search_entities, find_tags, get_insights that always injects the profile's
exclusions and only allows supported params, submit_candidates), each a thin
wrapper over ports that logs its call; a research agent with LangChain create_agent,
its system prompt built from the mode's research brief, and middleware limits
(ToolCallLimitMiddleware 12, ModelCallLimitMiddleware 8, ToolRetryMiddleware,
ModelFallbackMiddleware) plus a 25s timeout; and workflows/plan_session.py as an
outer LangGraph StateGraph: load_context -> research -> fallback (only if research
failed or returned too few) -> select_items -> resolve_media -> guardrails ->
compose. Build StandardMode (with the three cold-start tiers from CLAUDE.md),
WarmupMode (about 12 varied, popular, playable items; no prompts) and ModeRegistry;
TasteService.score using filter.results.entities with a same-type, closest-year
fallback; the LLM adapter with structured output and a template fallback; the
YouTube and demo media resolvers. Tests with a scripted fake chat model: empty
result -> next hint, limit -> fallback, exclusions always applied, guardrails,
duration, cold-start tiers, scoring fallback. Run ruff and pytest.
```

**Check:**
- Both sample profiles plan in under 25 seconds.
- A profile with only a birth year still gets a sensible session.
- The agent log shows the agent's own Qloo calls, including a recovery from an empty result.
- With the LLM switched off, the fallback still produces a session.

---

## Backend: sessions, feedback, shelf, warm-up (≈ 15 h)

### Backend 1. Migrations and repositories
Tables:
- `sessions`
- `session_items`
- `feedback`, with `actor`: `caregiver` or `person`
- `exclusions`
- `agent_runs`
- `media_cache`
- `qloo_cache`

### Backend 2. `SessionService`
- `plan` starts the agent run in the background and returns at once with status `planning`.
- A **state machine** for the statuses in the contract.

### Backend 3. Learning rules
In `domain/policies.py` (the agent owner reviews):
- the caregiver weights and the person-signal weights;
- each person signal counts once per item per day;
- the 0.6 threshold for becoming a signal;
- the ranking order;
- the era window.

### Backend 4. `FeedbackService`
- `rejected` adds an exclusion.
- `upset` hides the item and queues it for review.
- Person signals are accepted only for items on the profile's shelf. A skip counts only under 15 seconds.
- Everything is stored with its `actor`, for learning.

### Backend 5. `ShelfService` and its route
The shelf holds:
- verified favourites with playable media;
- items from approved sessions;
- the approved warm-up set.

It always leaves out excluded and hidden items.

### Backend 6. `WarmupService` and its route
- Pairs come from the latest approved warm-up set.
- The first pair is two items of different types or decades.
- After that, each pair is:
  - the most similar unseen item (using the agent's `TasteService.score`);
  - one different unseen item.
- It ends after `WARMUP_PAIRS` pairs.
- Each choice is recorded as a `chose` signal.

### Backend 7. Routes
The whole contract, with ownership checks.

### Backend 8. Rate limit and demo seed
- Rate-limit planning to 10 plans per hour per user.
- The demo seed also plans each demo profile's warm-up set in the background, as a draft, so it's ready for the judge to approve.

### Backend 9. Tests
- The state machine.
- An **excluded item never returns**, either in the next plan or on the shelf.
- The shelf shows only approved items.
- A skip after 15 seconds is ignored.
- A repeated tap on the same day counts once.
- Cross-user access is denied.

**Prompt for Claude Code:**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 2). Add SQLAlchemy models + Alembic
migration for sessions, session_items, feedback (with actor caregiver|person),
exclusions, agent_runs, media_cache, qloo_cache (RLS on, no policies); in-memory and
Postgres repositories. Implement domain/policies.py (weights from CLAUDE.md "Learning
rules", once per item per day for person signals, 0.6 threshold, ranking order, era
window); SessionService (plan runs the agent in the background, status state
machine); FeedbackService (rejected -> exclusion, upset -> hidden + review queue,
person signals only for shelf items, skip only under 15s); ShelfService; and
WarmupService (pairs from the latest approved warmup set: first pair different types
or decades, then most-similar via TasteService.score plus one different; stops after
WARMUP_PAIRS). Implement all Phase 2 routes with ownership checks, a 10/hour plan
rate limit, and warm-up drafts planned in demo/seed. API tests: plan -> approve ->
reject one item -> plan again -> item absent from plan and shelf; shelf only shows
approved items; skip >= 15s ignored; once-per-day signals; invalid status
transitions; cross-user 404. Run ruff and pytest.
```

**Check:** the API test (plan, approve, reject, plan again, the item is gone from the plan and the shelf) passes.

---

## Frontend: caregiver screens and Person mode (≈ 15 h)

### Frontend 1. Plan screen
- Session length: 10, 20 or 30 minutes.
- A "Plan today's session" button.
- An **agent log panel** that polls once a second, with `aria-live`.

### Frontend 2. Draft review
- Cards showing:
  - title, type and year;
  - "She was 17 when this came out";
  - the reason;
  - a source badge.
- Remove and reorder items.
- Edit a prompt.
- An **Approve** button.

### Frontend 3. Caregiver player
- YouTube IFrame, which never autoplays.
- Big controls and an always-visible **Stop**.
- Progress, and the prompt under each item.

### Frontend 4. Reaction buttons
- Reject asks for confirmation.
- Upset shows "Hidden. You can review it later."

### Frontend 5. Session complete
- A completion screen with a "Plan next session" button.
- The session's state survives a refresh.

### Frontend 6. Person mode (`/profiles/:id/person`, in the Person layout)

**First use (caregiver)**
- Shows the warm-up set.
- "Approve all", or remove items first.
- Then "Hand over".

**Warm-up**
- Two large cards.
- A tap sends the choice and shows the next pair.
- It ends on the shelf.

**Shelf**
- Large cards with title, type icon, year and decade colour.
- A tap plays the item.

**Player**
- Full screen, with a large **Stop**, **Play again** and **♥**.
- No autoplay chains.
- It sends `loved`, `replayed` and `skipped` (with `played_s`).

**Caregiver controls**
- A small caregiver button (long press) opens the reaction buttons.
- Leaving Person mode takes a 3-second long press.

**No prompts, reasons or other AI-written text anywhere in Person mode.**

### Frontend 7. Quality across all screens
- Phone layout.
- Keyboard access.
- Loading, empty and error states.

**Prompt for Claude Code (caregiver screens):**
```
Read CLAUDE.md and docs/API_CONTRACT.md (Phase 2). Build features/sessions and
features/agent-log: plan screen (length picker, plan button, agent log polling
/agent-runs/{id} every 1s with aria-live), draft review (item cards with
age-at-release, reason, source badge, remove/reorder, edit prompt, approve), player
(YouTube IFrame API, no autoplay, large controls, always-visible Stop, prompts),
reaction buttons (confirm on reject, "Hidden" notice on upset), completion screen.
State survives refresh. Phone layout, keyboard access, loading/empty/error states.
Run lint and build.
```

**Prompt for Claude Code (Person mode):**
```
Read CLAUDE.md ("Person mode") and docs/API_CONTRACT.md (Phase 2). Build
features/person-mode inside PersonLayout: a caregiver step that shows the warm-up
set draft with "Approve all" / remove / "Hand over"; the warm-up (two very large
cards from /warmup/next, tap to choose, ends on the shelf); the shelf (very large
cards: title, type icon, year, decade colour, room for an image later); a
full-screen player (huge Stop, Play again, ♥, no autoplay chains) that posts
loved / replayed / skipped with played_s to /person-signals; a long-press caregiver
button that opens reaction buttons; a 3-second long press to leave. No typing,
search, menus, prompts or reasons anywhere. Run lint and build.
```

**Check:**
- Run a whole session on a phone and on a laptop, including a refresh partway through.
- Do the warm-up and play from the shelf on a phone.

---

## Exit check (Monday night)

Locally (backend also run once from its Docker image):
1. Plan, approve, play, mark one item "sang along" and reject another.
2. In Person mode, approve the warm-up set, do the warm-up, play from the shelf and tap ♥.
3. Plan again.

**Done when:**
- The second session is different.
- The rejected item is gone everywhere.
- The log explains what changed, mentioning both the caregiver's reactions and the person's taps.

## If you miss it

- All three of you work only on this on Tuesday.
- Phase 3 shrinks to notes, backlinks and the list view.
- Phase 4 (Bridge) is cut.
- **Cut first in this phase:** the warm-up (keep the shelf), then editing prompts in the draft.
- **Never cut:** caregiver approval, Person mode showing only approved items, excluded items never returning, the agent log, an always-visible Stop.
