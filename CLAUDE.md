# CLAUDE.md: MeloMind

This file tells Claude Code how to work in this repo. Read it at the start of every session.
The plan, decisions, roles and risks are in `docs/PLAN.md`. Each phase's tasks are in their own file in `docs/phases/`.

**Current phase: 0, Kickoff and setup** (`docs/phases/phase-0-setup.md`). Update this line when a phase ends.

---

## What we're building

MeloMind helps families and caregivers of people living with dementia (including Alzheimer's) share personal music and memory sessions.

- **The caregiver** enters a few things the person loved when they were young. A birth year and a hometown are enough to start.
- **An AI agent** uses Qloo's taste graph to find songs, films, TV shows and books from the person's youth. It builds sessions of about 20 minutes, with a reason for every pick and gentle conversation prompts.
- **The person** chooses what to play by tapping large cards in **Person mode**.
- **The Memory Graph** keeps the memories that come up as linked notes about people, places, songs and decades. It also makes future prompts more personal.
- **The agent learns** from the caregiver's feedback and from what the person chooses.

### Who does what

| Role | Does |
|---|---|
| **The person** | Enjoys the sessions, and chooses by tapping cards in Person mode |
| **The caregiver** | Sets up the profile, approves everything the person sees, sits with them and uses the prompts, records reactions, adds memories, plans family visits, controls privacy |
| **The agent** | Finds what they're likely to love with Qloo, prepares sessions and the Person-mode shelf, suggests links between memories, learns from every reaction, and explains each step in the agent log |

### Context

This is an entry for the Qloo Agentic Hackathon.
- Judges score four criteria:
  - **Technological Implementation:** how well we use Qloo.
  - **Design:** a complete, coherent product.
  - **Potential Impact.**
  - **Quality of the Idea.**
- The rules require the app to be built with an agent framework, or to work as an agentic tool.

**Optimise for a reliable, explainable, working product, not for feature count.**

---

## Non-negotiable rules

### Product and safety
1. **The AI never converses with the person with dementia.** There's no chat and no voice. They choose by tapping cards in Person mode, and the caregiver stays in control.
2. It makes **no medical claims**. Never say it "treats", "improves memory", "reduces agitation" or anything similar.
3. **The caregiver approves** every session before it starts. **Person mode shows only items the caregiver has approved:** favourites they added, approved sessions and the approved warm-up set.
4. The **Stop** button is always visible, and media never autoplays.
5. **Person mode has no typing, search, menus, chat or AI-written text.** Leaving it needs a caregiver unlock.
6. An item marked **rejected never appears again** for that profile, anywhere.
7. An item marked **upset is hidden** and queued for the caregiver to review. **Only the caregiver** can hide or reject an item. A quick skip by the person only lowers its ranking.
8. Enforce rules 3, 6 and 7 **in code** (in the queries and the guardrails), never only in an LLM prompt.
9. **Never invent recommendations.** Every item must come from a Qloo result, a demo fixture or a verified favourite, and must record its `source` and `reason`.
10. Conversation prompts are open and gentle ("What does this song remind you of?"). They are never memory tests ("Do you remember…?").

### Data and secrets
11. Keys stay in **server environment variables only**: Qloo, LLM, YouTube, the Supabase secret key and `DATABASE_URL`. They never go in the frontend or in git.
12. **Never commit real Qloo API responses.** Demo fixtures are hand-written, marked `"demo": true`, and labelled "Demo data" in the UI.
13. Store the **minimum personal data**: display name, birth year, places, languages, favourites, feedback and memory notes. There are no health or diagnosis fields. Profiles and memories can be deleted.
14. **Memory notes are private** to their profile.
    - They're never sent to Qloo. Qloo only ever receives entity IDs and tags.
    - The AI sees a note's text only while suggesting links for it. When writing prompts, it sees only the titles of linked nodes that are allowed in prompts.
    - The note editor asks caregivers not to add medical details.
15. **Never send lyrics or song titles to Qloo**, because Qloo has no songs. **Never store or display lyrics** (copyright). A typed lyric is only a search hint: keep just the song title and artist.

### Code
16. Respect the **layer rule** (see Architecture). Business logic never goes in route handlers or React components.
17. Don't add dependencies, services or frameworks that aren't in the tech stack below without team agreement.
18. Build **one agent**, never a multi-agent system. It has three workflows that share the same tools:
    - planning a session;
    - resolving a favourite;
    - linking a memory note.

---

## Tech stack (decided)

Read the "Decisions" section of `docs/PLAN.md` before proposing a change.

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, httpx (async), pytest, ruff. uv manages Python, the virtual env and packages (`pyproject.toml` and `uv.lock`; no requirements files) |
| Agent | LangGraph for the outer workflows, plus LangChain's `create_agent` for the research step, bounded by middleware (`ToolCallLimitMiddleware`, `ModelCallLimitMiddleware`, `ToolRetryMiddleware`, `ModelFallbackMiddleware`). One LLM provider behind a port, with structured output and a template fallback. No Deep Agents |
| Database | Supabase Postgres via SQLAlchemy 2.0 (async, asyncpg), with Alembic migrations. The Memory Graph uses two ordinary tables, not a graph database |
| Auth | Supabase Auth, with anonymous sign-in for the demo. The backend verifies access tokens against the project's JWKS |
| Frontend | React 19, Vite, TypeScript (strict), React Router, TanStack Query, Tailwind and shadcn/ui. A graph library (react-force-graph or Cytoscape.js) for the Memory Graph view only |
| API types | Generated from FastAPI's OpenAPI schema with `openapi-typescript`. It needs TypeScript 5.x, so TypeScript stays pinned at 5.9 |
| Media | YouTube Data API v3 (`search`, `videos.list`) and the YouTube IFrame Player |
| Images | **None for now.** Cards use title, a type icon, the year and a decade colour. Images are a later decision |
| Testing | pytest (unit and API), `httpx.MockTransport` (Qloo contract tests), Playwright (one end-to-end judge path) |
| Hosting | Vercel (frontend), AWS Lightsail container service (backend), Supabase (database and auth). One monorepo |

Pin exact versions whenever you add a dependency: `uv add --bounds exact <package>` in `backend/` (writes `pyproject.toml` and `uv.lock`), and `npm install <package>` in `frontend/` (`.npmrc` sets `save-exact`).

---

## Repo layout

```
melomind/
├── CLAUDE.md
├── README.md
├── LICENSE                      MIT
├── docs/                        PLAN.md, phases/ (one file per phase), AGENT.md, QLOO_NOTES.md, API_CONTRACT.md
├── backend/
│   ├── app/
│   │   ├── main.py              app factory
│   │   ├── core/                settings, logging, base errors
│   │   ├── domain/              entities and pure rules (no I/O)
│   │   ├── application/
│   │   │   ├── ports.py         interfaces: TasteGraph, MediaResolver, LanguageModel, repositories
│   │   │   ├── services/        use cases: profiles, taste, sessions, feedback, shelf, memory
│   │   │   ├── agent/           workflows/ (plan_session, resolve_favourite, link_memory), nodes/, tools/, prompts/, state
│   │   │   └── modes/           session modes (Strategy) and the ModeRegistry
│   │   ├── infrastructure/
│   │   │   ├── qloo/            live HTTP adapter, fixture adapter, fixtures/
│   │   │   ├── media/           YouTube resolver, demo resolver
│   │   │   ├── llm/             provider adapter, template fallback
│   │   │   └── persistence/     SQLAlchemy models, Postgres and in-memory repositories
│   │   └── api/
│   │       ├── deps.py          composition root: builds and wires everything
│   │       ├── errors.py        maps domain errors to HTTP
│   │       └── v1/              routes/, schemas/, router.py
│   ├── alembic/
│   ├── tests/                   unit/, api/, contract/
│   └── scripts/                 qloo_smoke.py (manual only, never in CI)
├── frontend/src/
│   ├── app/                     shell, routes, providers
│   ├── pages/                   route-level pages that compose features
│   ├── features/<name>/         e.g. profiles, sessions, agent-log, person-mode, memory-graph
│   └── shared/                  api/ (typed client and generated schema), ui/, hooks/, types/
└── e2e/                         Playwright tests
```

---

## Architecture

### Layers and the dependency rule

| Layer | Contains | May import |
|---|---|---|
| `domain` | dataclasses, enums, pure functions | nothing from the app |
| `application` | services (use cases), ports, the agent, modes | `domain` |
| `infrastructure` | adapters that implement ports (httpx, SQLAlchemy, SDKs) | `application`, `domain` |
| `api` | thin routes, Pydantic schemas, error mapping, `deps.py` | everything (composition root) |
| `core` | settings, logging, base errors | nothing from the app |

**Imports point inwards only.**
- No FastAPI, Pydantic, SQLAlchemy or httpx in `domain`.
- No concrete adapters in `application`; it uses ports only.

### Patterns
- **Ports and adapters:** live Qloo and demo fixtures both implement `TasteGraph`. Postgres and in-memory storage both implement the repositories. Fakes are used in tests and in demo mode.
- **Strategy and registry:** session modes.
- **Hybrid agent:** fixed LangGraph workflows, with one tool-calling research step (`create_agent`).
- **Composition root:** `api/deps.py` is the only place that chooses adapters. It uses live Qloo when `QLOO_API_KEY` is set, and fixtures otherwise.

### The agent (`application/agent/`)

There is **one agent, built as a hybrid**:
- fixed LangGraph workflows where **code controls the order**;
- one **research step** where the AI decides its own Qloo calls (LangChain `create_agent`).

**Tools** (`agent/tools/`). Each is a thin wrapper over a port, and every call is logged.

| Tool | What it does |
|---|---|
| `search_entities(name, type?)` | Qloo `/search`. Returns matches with type and year |
| `find_tags(query)` | Qloo `/v2/tags` |
| `get_insights(type, signals, era?, country?, popularity_min?, take)` | Qloo `/v2/insights`. **Always adds the profile's exclusions itself**, and allows only supported parameters |
| `find_memory_nodes(query, kind?)` | Existing people, places and other nodes in this profile's Memory Graph |
| `compare_tastes(group_a, group_b)` | Qloo `/v2/insights/compare` (Phase 4, Bridge) |
| `submit_candidates(...)` / `propose_matches(...)` / `propose_links(...)` | The agent's final, structured answer |

**Limits** (LangChain middleware on `create_agent`):
- `ToolCallLimitMiddleware`: at most 12 Qloo calls per planning run, 5 searches per favourite, and 10 per memory note.
- `ModelCallLimitMiddleware`: at most 8 model calls per run.
- `ToolRetryMiddleware` for temporary errors.
- `ModelFallbackMiddleware` for a backup model.
- A 25-second overall timeout.

When a limit is hit or the agent fails, the **rule-based fallback** takes over, so a result is always produced.

#### Workflow 1: plan a session (`workflows/plan_session.py`)

| # | Step | Who decides |
|---|---|---|
| 1 | `load_context`: profile, verified favourites, caregiver and person feedback, exclusions, learned weights, confirmed memory links | Code |
| 2 | `research`: the agent gets the mode's brief (goal, entity mix, era, country, popularity floor, caregiver instructions), calls tools until it has enough candidates, then submits them | **AI agent** |
| 3 | `fallback`: runs only if research failed, hit a limit or returned too few. Runs the mode's fixed queries, relaxing them up to 2 times | Code |
| 4 | `select_items`: rank by Qloo affinity, then learned weight, then popularity; pick the mode's mix plus spares | Code |
| 5 | `resolve_media`: find playable videos; replace unplayable items with spares | Code |
| 6 | `guardrails`: remove blocked items, require a source on every item, fit the target length (±10 %) | **Code only** |
| 7 | `compose`: reasons and conversation prompts, made personal with confirmed memories linked to each item | AI, with a template fallback |

#### Workflow 2: resolve a favourite (`workflows/resolve_favourite.py`)

The caregiver can type a name, a song title, a remembered lyric or a description. The agent climbs the **hint ladder** and stops at the first good match:
1. **Interpret the input:** the AI guesses the song, singer, composer, film and year.
2. Search Qloo for the **singer**.
3. Try **spelling variants**.
4. Search the **composer or music director**.
5. Search the **film** the song comes from.
6. Search the film's **lead actor**.
7. Use a **genre or region tag** as the signal.
8. **Ask the caregiver** for a hint: singer, film or year.
9. Otherwise **keep it as text**. It can still be played and used in prompts, but it isn't a Qloo signal.

Rules for this workflow:
- **Never search Qloo for lyrics or song titles.** Qloo has no songs.
- Accept a match only after checking its **type, year and name**, not just that the result isn't empty.
- Return up to 3 proposals.
- **The caregiver confirms** a proposal before it's saved as a verified favourite. Only verified favourites become Qloo signals.

#### Workflow 3: link a memory note (`workflows/link_memory.py`)
1. **Extract mentions** (LLM, structured output): people, places, years or decades, songs, artists, films and books.
2. **Resolve songs, artists, films and books** with the hint ladder from Workflow 2.
3. **Match people and places** to existing Memory Graph nodes with `find_memory_nodes`, or propose new nodes.
4. **Return suggested links.** The caregiver confirms each one with ✓ or ✗.

Confirmed links are saved. A confirmed song or film can become a favourite, and so a Qloo signal, with one more tap.

#### For all workflows
- **Every tool call and decision goes into the agent log** in plain English. For example: "Searched singer Y → no match. Tried composer Z → found (artist) ✓."
- The log is saved in `agent_runs` and shown in the UI.
- Nodes and tools depend on ports only. The workflow builders inject them.
- The research agent compiles to a LangGraph graph, so it runs as one node inside the outer workflow.

### Session modes (`application/modes/`)
- `SessionMode` has four methods:
  - `research_brief(state)`: the goal and constraints given to the research agent;
  - `fallback_queries(state)`: the rule-based query plan;
  - `relax(queries, attempt)`: looser queries for a fallback retry;
  - `select(ranked, state)`: picks the mix, plus spares.
- Modes register in `ModeRegistry`.
- `standard` and `warmup` (the Person-mode warm-up set) come first. `bridge` (elder plus visitor) is added in Phase 4.
- **Adding a mode must not require changes to the workflows or the API.**

### Cold start: the first recommendations

Qloo needs no history. The first session uses whatever the family gives:

| The family gives | The research brief and fallback use |
|---|---|
| **3 or more favourites** | The favourites as signals. Qloo expands them straight away |
| **1–2 favourites or a hint** | The hint ladder's result (singer, film or tag), plus era and country |
| **Nothing specific** | Birth year (era), where they grew up (region), language, `signal.demographics.age=55_and_older` and a high popularity floor: the big hits of their youth |

**Onboarding**
- Only the display name and birth year are required.
- Every other question has a **"Not sure, skip"** option.

**First use of Person mode**
- It starts with a **"this or that" warm-up**, which finds a direction within a few taps.
- The `warmup` mode plans the warm-up set: about 12 varied, well-known items from their youth. The caregiver approves it like any session.

### Person mode

**The shelf** shows large cards of:
- verified favourites that have a playable video;
- items from approved sessions;
- the approved warm-up set.

Only items with a playable video appear. Excluded and hidden items never appear.

**The warm-up** ("this or that")
- Two large cards at a time.
- It uses only the approved warm-up set. The caregiver can "Approve all" in one tap, or remove items first.
- After each tap, the next pair has:
  - the unseen item **most similar** to the chosen one (Qloo scores the set with the chosen item as the signal; if that fails, the same type and the closest year);
  - one **different** item (another type or decade), to keep exploring.
- It ends after `WARMUP_PAIRS` pairs, or when the set runs out.
- The card that wasn't chosen gets no signal. Not choosing isn't disliking.

**The player**
- Full screen, with a large **Stop**, **Play again** and **♥**.
- No autoplay chains.
- A small caregiver button (long press) opens the caregiver's reaction buttons, so an upsetting item can be hidden at once.

**Person mode never shows prompts, reasons or any other AI-written text.** Prompts are for the caregiver.

**Cards** show the title, a type icon, the year and a decade colour. There are no images for now.

**Leaving Person mode** needs a caregiver unlock: a 3-second long press. A PIN is a stretch goal.

**Signals** are stored as feedback with `actor = person` (see Learning rules).

### Memory Graph

**Node kinds:** `person`, `place`, `decade`, `memory` (a note), `song`, `artist`, `movie`, `tv_show`, `book`, `session`.
- Any node can have body text and a year. Artist, film, TV and book nodes also carry a Qloo ID.
- Each node has a **"Use in prompts"** switch, on by default. The caregiver turns it off for anyone or anything that shouldn't come up, such as someone who has died.

**Links**

Each link has a **kind**:
- `mentions`
- `because_of` (from Qloo)
- `reacted` (from a session)
- `from_movie`
- `in_decade`
- `lived_in`
- `related`

It also records a **source** (caregiver, agent, Qloo or session) and a **status**: `suggested`, `confirmed` or `rejected`. A rejected suggestion is never suggested again.

**How links are made**
1. The agent suggests them for each memory note (Workflow 3), and the caregiver confirms each one.
2. Typing `[[` opens a picker for linking by hand.
3. Automatic links are created for:
   - favourites;
   - places lived (`lived_in`);
   - decades (`in_decade`);
   - session items that got a positive reaction (sang along, smiled) or a ♥. They get a `reacted` link from the session and a `because_of` link to the favourite that led to them.

Other session items don't become nodes, so the graph stays about what mattered.

**Views**
- A node page with **backlinks**.
- A **graph view**, capped at `MEMORY_GRAPH_MAX_NODES` (30) and grouped by decade.
- A **timeline** by decade.
- A **list view**, always available, for phones and screen readers.

**What it's used for**
- Personal prompts in `compose`, using only confirmed links to nodes with "Use in prompts" on.
- One-tap promotion of confirmed songs, artists, films, TV shows and books to favourites.

**Storage:** two Postgres tables, `memory_nodes` and `memory_links`.

Suggested links appear only in the suggestions panel. Only confirmed links appear in the views or affect prompts and signals.

### Learning rules (`domain/policies.py`)

**Era window:** `birth_year + 13` to `birth_year + 21`, widened by 5 years per fallback retry.

**Caregiver reactions** (`actor = caregiver`):

| Reaction | Effect |
|---|---|
| `sang_along` | 1.0 |
| `smiled` | 0.6 |
| `calm` | 0.2 |
| `neutral` | 0 |
| `upset` | Suppress the item and queue it for review |
| `rejected` | Exclude the item |

**Person-mode signals** (`actor = person`):

| Signal | Effect |
|---|---|
| `chose` | 0.3 |
| `loved` (♥) | 0.6 |
| `replayed` | 0.6 |
| `skipped` within 15 seconds | −0.2 (lowers ranking only; never hides) |

Each person signal counts at most once per item per day, so repeated taps don't inflate a weight.

**Feedback into Qloo**
- Items with a total weight ≥ 0.6 become Qloo signals next time.
- Blocked items go into `filter.exclude.entities`, and the guardrails remove them again.

**Ranking:** Qloo affinity first, then learned weight, then popularity.

These are heuristics. Never describe them as clinically validated.

---

## Qloo reference

The full notes are in `docs/QLOO_NOTES.md`.

**Calling it**
- Base URL: `https://hackathon.api.qloo.com`. The hackathon key returns 401 on any other host.
- Send the key in the `X-Api-Key` header.
- Every call is a GET with query parameters.

**Endpoints**
- `/search`: turns names into entity IDs.
- `/entities`: gets details for IDs.
- `/v2/insights`: recommendations. `filter.type` is required.
- `/v2/tags`: tag IDs.
- `/v2/insights/compare` and `/analysis`: check how they behave before relying on them.
- **Never call `/recommendations` or `/recs`.**

**Entity types we use:** `urn:entity:artist`, `movie`, `tv_show` and `book`.
- Qloo has **no song type and no lyrics**. Store songs as text, and use the singer, composer or film as the signal. Never search Qloo for a song title or a lyric.

**Parameters we use**
- `signal.interests.entities`
- `signal.interests.tags`
- `signal.demographics.age=55_and_older`
- `filter.release_year.min` and `.max` (movies and TV)
- `filter.publication_year.min` and `.max` (books)
- `filter.release_country`
- `filter.popularity.min`
- `filter.exclude.entities`
- `filter.exclude.tags`
- `filter.results.entities`: scores a given set, used by the Person-mode warm-up. Check it works.
- `take`: the default is 5, so **always set it**.

**Gotchas**
- **Invalid parameters are silently ignored.** When results are empty, check the parameter guide.
- **Some entities and regions have little data.** Follow the hint ladder, logging each step.
- Cache responses on the server (`qloo_cache` table), **never in the repo**.

---

## Media (YouTube)

- The default quota is about **100 searches a day**, so:
  - cache every lookup in `media_cache`;
  - resolve media only for items chosen for a session or the shelf;
  - pre-warm the demo profiles.
- Before using a video, call `videos.list` to check that `status.embeddable` is true, and read `contentDetails.duration`.
- If nothing is playable, mark the item "No playable version found" and use a spare. **Never substitute an unrelated video.**
- Embedded videos can show ads, and we can't control that. List it under known limitations.

---

## LLM rules

- Use one provider behind the `LanguageModel` port. Set the model name in the environment.
- Validate output against Pydantic schemas. On invalid output, fall back to templates.
- Use a low temperature for planning, and a 15-second timeout that triggers the template fallback.
- Send only what's needed:
  - first name, birth year, places and favourites;
  - the text of a memory note, only while suggesting links for it;
  - the titles of linked nodes that are allowed in prompts, only while writing prompts.
- Never send keys or other personal data.
- Put a spending cap on the account, and rate-limit planning per user.
- Anything the AI infers is a **proposal** that the caregiver confirms. This includes a song from a lyric, a match from a description, and a link from a note.
- Only confirmed favourites and links affect Qloo signals.

---

## API conventions

**Routes and schemas**
- All routes live under `/api/v1`. JSON uses snake_case.
- Pydantic schemas go in `api/v1/schemas/`.

**Auth**
- Requests send `Authorization: Bearer <Supabase access token>`.
- Verify it with PyJWT's `PyJWKClient` against `https://<project>.supabase.co/auth/v1/.well-known/jwks.json`.
- Check `exp`, `iss` and `aud` (`authenticated`). Anonymous users are valid users.
- **Every profile-scoped route checks ownership.** Return 404, not 403, for someone else's resource.

**Errors**
- Domain errors return `{ "error", "detail" }` with status 404, 422 or 502.
- Never put stack traces in responses.

**Keeping in sync**
- Update `docs/API_CONTRACT.md` in the same PR as any endpoint change.
- Regenerate the frontend types (`npm run gen:api`) after any endpoint change.

---

## Frontend conventions

**Structure**
- One folder per feature in `src/features/<name>/`. Pages only compose features.
- Use TanStack Query for server state only. Don't add a global store unless the team agrees.
- Call the API only through `src/shared/api`, which is typed from the generated schema.

**Caregiver screens:** calm and clear.
- Base font of at least 18 px; tap targets of at least 44 px; high contrast.
- No flashing or auto-advancing content.
- Everything works from the keyboard.
- `aria-live` on the agent log.

**Person mode:** simpler still.
- Very large cards, with at most 2 choices on screen during the warm-up.
- Minimal text.
- No time limits.
- A large Stop button.
- No navigation away without the caregiver unlock.

**Cards:** title, type icon, year and decade colour. No images for now.

**States and badges**
- Always show loading, empty and error states.
- Recommendations show a "Demo data" or "Live Qloo" badge.

---

## Code style

**Python**
- Type hints everywhere.
- `ruff format` and `ruff check` must be clean.
- Small functions; async I/O.
- Dataclasses in the domain; Pydantic only at the API and LLM edges.
- No global mutable state except the cached settings.

**TypeScript**
- Strict mode, no `any`.
- Function components and hooks, named exports.
- ESLint and Prettier must be clean.

**Both**
- Clear names, and docstrings or JSDoc on public classes and functions.
- No dead or commented-out code.
- No TODO without an issue number.

---

## Testing

**Unit tests** (fast, no network):
- domain policies;
- each agent node;
- each tool;
- the guardrails;
- the modes.

**API tests:** FastAPI `TestClient` with in-memory repositories and the fixture adapters.

**Contract tests:** the Qloo HTTP adapter with `httpx.MockTransport` (parameter building, parsing, retries).

**Agent tests:** a scripted fake chat model that returns predefined tool calls, never a real LLM.

**Must-have tests:**
- an excluded item never returns, in sessions or in Person mode;
- an upset item is hidden;
- Person mode shows only approved items;
- cross-user access is denied;
- a Qloo timeout or empty result is handled;
- an LLM failure falls back to templates;
- session length is within ±10 % of the target;
- the research agent stops at its limits, and the fallback still produces a session;
- `get_insights` always applies the profile's exclusions;
- memory note text never reaches the Qloo adapter;
- suggested links don't affect signals or prompts until confirmed;
- nodes with "Use in prompts" off never reach `compose`;
- a rejected link suggestion is never suggested again.

**End-to-end (Phase 4):** Playwright runs the judge path (see `docs/PLAN.md`) against a local stack, and by hand after the Thursday-night deploy.

**Never call live Qloo, YouTube or the LLM in CI.**

---

## Commands

```bash
# backend (uv reads .python-version and uses Python 3.12)
cd backend && uv sync                  # creates .venv and installs everything from uv.lock
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run alembic upgrade head
uv add --bounds exact <package>        # add a dependency (--dev for dev tools)

# frontend
cd frontend && npm install
cp .env.example .env.local             # once; sets VITE_API_BASE_URL
npm run dev                            # http://localhost:5173
npm run build && npm run lint
npm run gen:api                        # regenerate API types from the backend's /openapi.json

# end-to-end
cd e2e && npx playwright test
```

---

## Environment variables

**Backend**
- App and database:
  - `APP_ENV`
  - `FRONTEND_ORIGIN`
  - `DATABASE_URL`
- Supabase: `SUPABASE_URL`
- Qloo:
  - `QLOO_API_KEY` (empty means demo fixtures)
  - `QLOO_BASE_URL`
- YouTube: `YOUTUBE_API_KEY`
- LLM:
  - `LLM_PROVIDER`
  - `LLM_MODEL`
  - `LLM_API_KEY`
- Agent and limits:
  - `AGENT_MAX_TOOL_CALLS=12`
  - `AGENT_MAX_MODEL_CALLS=8`
  - `AGENT_TIMEOUT_SECONDS=25`
  - `RESOLVE_MAX_SEARCHES=5`
  - `LINK_MAX_SEARCHES=10`
  - `AGENT_MAX_RETRIES=2` (fallback relaxations)
  - `SESSION_TARGET_MINUTES=20`
  - `PLAN_RATE_LIMIT_PER_HOUR`
- Person mode and Memory Graph:
  - `WARMUP_PAIRS=6`
  - `MEMORY_GRAPH_MAX_NODES=30`

**Frontend**
- `VITE_API_BASE_URL`
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_PUBLISHABLE_KEY`

Keep both `.env.example` files up to date. Never commit `.env`.

---

## Git workflow

- One branch per task: `feat/<area>-<name>`, `fix/…` or `docs/…`.
- Use conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`.
- Open a pull request into `main`. It needs one review and green CI.
- The PR description covers what changed, why, how it was tested, and a screenshot for UI changes.
- Keep pull requests small, ideally under about 400 changed lines.

---

## How to add a feature

**A session mode**
1. Add `application/modes/<name>.py` implementing `SessionMode`.
2. Register it.
3. Add tests.
4. The plan endpoint accepts `mode: "<name>"` with no other changes.

**An agent step**
1. Add a node in `application/agent/nodes/` that does one job and writes to the log.
2. Wire it into the workflow in `application/agent/workflows/`.
3. Add a unit test.

**An agent tool**
1. Add it in `application/agent/tools/` as a thin wrapper over a port. Validate its inputs and log every call.
2. Add it to the tool list of the workflow that needs it.
3. Test it with the scripted fake model.

**An external service**
1. Add a port in `application/ports.py`.
2. Add an adapter and a fake in `infrastructure/<service>/`.
3. Wire it in `api/deps.py`.

**An endpoint**
1. Add the schema in `api/v1/schemas/` and the route in `api/v1/routes/`, calling a service.
2. Register it in `router.py`.
3. Update `API_CONTRACT.md`.
4. Run `gen:api`.

**A frontend page**
1. Add the feature folder.
2. Add the page in `pages/` and the route in `app/`.
3. Add loading, empty and error states.

---

## Definition of done

- Merged into `main`, with tests for any new logic.
- Working locally at phone width, and in Docker for backend changes.
- Contract and docs updated.
- Demo data labelled as demo data.

---

## How Claude should work here

**Before coding**
- Read your task in the current phase's file in `docs/phases/`.
- Restate the plan and list the files you'll touch.
- Ask before changing an API contract, a decision or another person's folder.

**While coding**
- Stay within the task's scope. Don't refactor unrelated code.
- If something doesn't fit the layer rule, ask rather than bend the rule.
- Prefer simple, readable code to clever abstractions. This is a 9-day build.

**After coding**
- Run the relevant checks: `pytest` and `ruff` for the backend, `lint` and `build` for the frontend.
- Report the results honestly. Never say tests pass without running them.

**Always**
- Never commit secrets or real Qloo data. Never add live API calls to tests.
- If you're unsure about a Qloo parameter or response shape, check `docs/QLOO_NOTES.md`. If it's still unclear, say so instead of guessing.
