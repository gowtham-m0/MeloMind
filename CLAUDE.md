# CLAUDE.md: MeloMind

This file tells Claude Code how to work in this repo. Read it at the start of every session.
The plan, decisions, roles and risks are in `docs/PLAN.md`. Each phase's tasks are in their own file in `docs/phases/`.

**Current phase: 4, Polish and freeze** (`docs/phases/phase-4-bridge-and-freeze.md`). Update this line when a phase ends.

> **Pivot, 24 Oct 2026.** MeloMind was a dementia music-session tool. It is now a **personal taste dashboard**. Code from Phases 0–1 and parts of the old Phase 2 are reused (see the phase file). Anything in the code about caregivers, sessions, Person mode or the warm-up shelf is being removed.

---

## What we're building

MeloMind is **your taste, in one home screen**. Like opening YouTube, Spotify or Netflix, you land on rows of things picked for you, except MeloMind spans **music, films, TV shows and books** at once, and it tells you *why* each pick is there.

- **You** add a few favourites (search and tap), take a quick "this or that" taste quiz, and you're in.
- **An AI agent** uses Qloo's taste graph to build your **feed**: a hero pick and rows like "For you", "Because you liked Arctic Monkeys", "Films for you", "Books for you" and "Popular in India". Every card has a **thumbnail**, a one-line reason, and a link that **opens it where it lives**: YouTube or Spotify for music, Netflix, Prime Video, JioHotstar and others for films and TV, Google Books or Goodreads for books.
- **Your taste updates** from what you do: like, save, open, "not interested". Refresh and the rows change, and the agent log says what changed.
- **Your journal** is an everyday diary you **write or speak**. The agent spots the artists, films, shows and books you mention, you confirm them with one tap, and they shape your feed ("From your journal").
- **Your taste page** shows what MeloMind has learned: top genres and tags, your favourites, and a **taste map** of how your likes connect.

### Who does what

| Role | Does |
|---|---|
| **You (the user)** | Add favourites, take the taste quiz, browse the feed, like / save / dismiss, open items on their platform, write or speak journal entries, confirm what the agent found |
| **The agent** | Finds what you'll probably like with Qloo, builds the feed rows, explains every pick, reads journal entries for mentions, learns from every signal, and writes each step to the agent log |

### Context

This is an entry for the Qloo Agentic Hackathon.
- Judges score four criteria:
  - **Technological Implementation:** how well we use Qloo.
  - **Design:** a complete, coherent product. **UI/UX is our main lever.**
  - **Potential Impact.**
  - **Quality of the Idea.**
- The rules require the app to be built with an agent framework, or to work as an agentic tool.

**Optimise for a beautiful, reliable, explainable product, not for feature count.**

---

## Non-negotiable rules

### Product
1. **Never invent recommendations.** Every item must come from a Qloo result, a demo fixture or a verified favourite, and must record its `source` and `reason`.
   - **Songs are a lookup, never a recommender.** A song card is a top track of an artist Qloo already picked, looked up in Apple's iTunes catalogue (`source: song_catalogue`). iTunes receives only the artist name Qloo returned: never user text, lyrics or journal content.
2. **Every pick is explainable.** Each card has a reason and a `because_of` signal, and the agent log says how the feed was built.
3. An item marked **not interested never appears again** for that profile, in any row, until the user undoes it in Settings.
4. **Anything the AI infers is a proposal** the user confirms: a song from a lyric, a match from a description, an item mentioned in a journal entry. Only confirmed items become taste signals.
5. **Platform links are honest.** A search link is labelled "Search on Netflix", never "Watch on Netflix". "Watch on" / "Listen on" is only for a direct link from a known external ID.
6. **No autoplay.** Media and previews play only when the user taps.
7. Enforce rules 1, 3 and 4 **in code** (in the queries and the guardrails), never only in an LLM prompt.

### Data and secrets
8. Keys stay in **server environment variables only**: Qloo, LLM, YouTube, the Supabase secret key and `DATABASE_URL`. They never go in the frontend or in git.
9. **Never commit real Qloo API responses.** Demo fixtures are hand-written, marked `"demo": true`, and labelled "Demo data" in the UI.
10. Store the **minimum personal data**: display name, optional birth year and country, favourites, feedback and journal entries. Profiles and journal entries can be deleted.
11. **Journal entries are private** to their profile.
    - They're never sent to Qloo. Qloo only ever receives entity IDs and tags.
    - The AI sees an entry's text only while suggesting links for it, and only through Groq (never a free-tier Gemini key).
    - Voice recordings are transcribed and then discarded. Audio is never stored.
12. **Never send lyrics or song titles to Qloo**, because Qloo has no songs. **Never store or display lyrics** (copyright). A typed lyric is only a search hint: keep just the song title and artist.
13. **Images are URLs only.** We show Qloo's image URL, an Open Library cover URL or an iTunes artwork URL. We never download, store or re-host images or song previews.

### Code
14. Respect the **layer rule** (see Architecture). Business logic never goes in route handlers or React components.
15. Don't add dependencies, services or frameworks that aren't in the tech stack below without team agreement.
16. Build **one agent**, never a multi-agent system. It has three workflows that share the same tools:
    - building the feed;
    - resolving a favourite;
    - linking a journal entry.

---

## Tech stack (decided)

Read the "Decisions" section of `docs/PLAN.md` before proposing a change.

| Area | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, httpx (async), ruff. uv manages Python, the virtual env and packages (`pyproject.toml` and `uv.lock`; no requirements files) |
| Agent | LangGraph for the outer workflows, plus LangChain's `create_agent` for the research step, bounded by middleware (`ToolCallLimitMiddleware`, `ModelCallLimitMiddleware`, `ToolRetryMiddleware`, `ModelFallbackMiddleware`). The LLM sits behind one port: Gemini (`gemini-3.8-flash`) as the main model and Groq (`openai/gpt-oss-120b`) as the fallback, built by a factory in `infrastructure/llm/`, with structured output and a template fallback (`langchain-groq`, `langchain-google-genai`). No Deep Agents |
| Speech to text | Groq Whisper (`whisper-large-v3-turbo`) behind a `SpeechToText` port, using the Groq key (`LLM_FALLBACK_API_KEY`). The browser records with `MediaRecorder` |
| Database | Supabase Postgres via SQLAlchemy 2.0 (async, asyncpg), with Alembic migrations. Journal links and the taste map use two ordinary tables, not a graph database |
| Auth | Supabase Auth, with anonymous sign-in for the demo. The backend verifies access tokens against the project's JWKS |
| Frontend | React 19, Vite, TypeScript (strict), React Router, TanStack Query, Tailwind and shadcn/ui, **rebuilt from scratch in Phase 2** (see "Design system"). A graph library (react-force-graph or Cytoscape.js) for the taste map only |
| API types | Generated from FastAPI's OpenAPI schema with `openapi-typescript`. It needs TypeScript 5.x, so TypeScript stays pinned at 5.9 |
| Images | Qloo `properties.image` URLs for artists, films and TV; Open Library covers by ISBN for books (`https://covers.openlibrary.org/b/isbn/<isbn13>-L.jpg`, no key); a gradient tile with a type icon as the fallback |
| Platform links | Built in code from the title, type, year, country and any Qloo external ID (`domain/links.py`). No streaming-availability API |
| Songs | Apple's iTunes Search API (`/search`, no key) behind a `SongCatalog` port (`infrastructure/music/itunes.py`): top songs for artists Qloo picked, with artwork, a 30-second preview URL and the Apple Music store link. In-memory cache (6 hours) and about 18 calls a minute. `SONGS_ENABLED=false` turns it off |
| Media preview (optional) | YouTube Data API v3 (`search`, `videos.list`) and the YouTube IFrame Player, **only on demand** from an item's detail view. Songs use their iTunes preview instead |
| Hosting | Vercel (frontend), AWS Lightsail container service (backend), Supabase (database and auth). One monorepo |

Pin exact versions whenever you add a dependency: `uv add --bounds exact <package>` in `backend/` (writes `pyproject.toml` and `uv.lock`), and `npm install <package>` in `frontend/` (`.npmrc` sets `save-exact`).

---

## Repo layout

```
melomind/
├── CLAUDE.md
├── README.md
├── LICENSE                      MIT
├── image.png                    reference mockup for the feed layout (not its colours)
├── .claude/skills/              shared design skills: impeccable, emil-design-eng, animate, review-animations, improve-animations, break-ui
├── docs/                        PLAN.md, phases/ (one file per phase), AGENT.md, QLOO_NOTES.md, API_CONTRACT.md
├── backend/
│   ├── app/
│   │   ├── main.py              app factory
│   │   ├── core/                settings, logging, base errors
│   │   ├── domain/              entities and pure rules (no I/O): models, feed, links, policies
│   │   ├── application/
│   │   │   ├── ports.py         interfaces: TasteGraph, MediaResolver, LanguageModel, SpeechToText, repositories
│   │   │   ├── services/        use cases: profiles, taste, feed, feedback, quiz, journal, taste_profile
│   │   │   ├── agent/           workflows/ (build_feed, resolve_favourite, link_journal), nodes/, tools/, prompts/ (with the template fallback), state
│   │   │   └── rows/            feed row strategies and the RowRegistry
│   │   ├── infrastructure/
│   │   │   ├── qloo/            live HTTP adapter, fixture adapter, fixtures/
│   │   │   ├── media/           YouTube resolver (optional preview), demo resolver
│   │   │   ├── music/           iTunes song catalogue (songs for Qloo-picked artists)
│   │   │   ├── llm/             chat-model factory (Groq, Gemini), the LanguageModel adapter, Groq Whisper
│   │   │   └── persistence/     SQLAlchemy models, Postgres and in-memory repositories
│   │   └── api/
│   │       ├── deps.py          composition root: builds and wires everything
│   │       ├── errors.py        maps domain errors to HTTP
│   │       └── v1/              routes/, schemas/, router.py
│   ├── alembic/
│   └── scripts/                 qloo_smoke.py (manual only, never in CI)
├── frontend/src/
│   ├── app/                     shell, routes, providers, theme
│   ├── pages/                   route-level pages that compose features
│   ├── features/<name>/         e.g. onboarding, feed, item-detail, taste, journal, taste-map, agent-log, settings
│   └── shared/                  api/ (typed client and generated schema), ui/ (design system), hooks/, types/
```

---

## Architecture

### Layers and the dependency rule

| Layer | Contains | May import |
|---|---|---|
| `domain` | dataclasses, enums, pure functions | nothing from the app |
| `application` | services (use cases), ports, the agent, row strategies | `domain` |
| `infrastructure` | adapters that implement ports (httpx, SQLAlchemy, SDKs) | `application`, `domain` |
| `api` | thin routes, Pydantic schemas, error mapping, `deps.py` | everything (composition root) |
| `core` | settings, logging, base errors | nothing from the app |

**Imports point inwards only.**
- No FastAPI, Pydantic, SQLAlchemy or httpx in `domain`.
- No concrete adapters in `application`; it uses ports only.

### Patterns
- **Ports and adapters:** live Qloo and demo fixtures both implement `TasteGraph`. Postgres and in-memory storage both implement the repositories. Fakes are used in tests and in demo mode.
- **Strategy and registry:** feed rows (`application/rows/`).
- **Hybrid agent:** fixed LangGraph workflows, with one tool-calling research step (`create_agent`).
- **Composition root:** `api/deps.py` is the only place that chooses adapters. It uses live Qloo when `QLOO_API_KEY` is set, and fixtures otherwise.

### Profiles
- A user can have several **profiles**, Netflix-style (a profile picker on sign-in). Each profile has its own favourites, feedback, feed and journal.
- Only the display name is required. Country and birth year are optional ("Skip"). Country drives "Popular in <country>" and platform links. Birth year only powers the optional "Throwback" row.

### The feed

The home screen. It's a saved snapshot (`feeds` table), so it opens instantly. **Refresh** (or new feedback, after a short debounce) starts a new `build_feed` run in the background, and the UI swaps in the new feed when it's done.

**Layout** (desktop; the reference mockup is `image.png` in the repo root: take its layout and features, not its dark purple look)
- **Left sidebar:** logo with the tagline "Your personal culture companion"; nav (Home, Discover, Music, Movies & TV, Books, Journal, Saved, Taste); **Your taste profile** tag chips with "+ Add more"; a small "Keep exploring" nudge at the bottom. On phones it becomes a bottom tab bar (Home, Discover, Journal, Saved, Taste).
- **Top bar:** one global search ("Search artists, films, books or anything…") using taste search, and the profile menu ("Hey, Aanya").
- **Main column:**
  1. **Hero banner:** the top pick's image, a bold headline with one amber-highlighted word, its reason, and "Open on…" plus "Why this?".
  2. **Category tiles:** Music, Movies & TV, Books (image tiles that open the filtered Discover page).
  3. **Rows**, each from a row strategy, with a title, a one-line subtitle and "See all".
- **Right rail:**
  - **Your vibe today:** mood chips (Chill, Happy, Focused, Melancholy, Energetic) and "Get recommendations" (Phase 4: an extra row built from mood tags);
  - **Quick actions:** Surprise me, Watch something new, Find a book to read, Write in your journal;
  - **Cross-culture picks:** "Because you like The 1975…" with one item per type, each labelled Watch, Read or Listen.
- On tablets the right rail moves under the hero; on phones its sections become rows.

**Rows**, in this order when they have items:

| Row key | Title | Built from |
|---|---|---|
| `for_you` | Recommended for you | The research agent's mixed candidates, all types |
| `cross_culture` | Cross-culture picks (right rail) | One insights call per other type with the newest strong signal: "Because you like The 1975" → a film, a show, a book, an artist |
| `because_<ref>` | Because you liked X | One insights call with the top 1–2 liked or favourite items as the signal |
| `journal` | From your journal | Signals from confirmed journal links: one insights call per type (at most two) |
| `music` | Music for you | Artists from the pool, topped up with an artist insights call |
| `songs` | Songs for you | Not a row strategy: the `add_songs` node, after `build_rows`. Two top songs each from the first 6 artists in the feed, from the song catalogue. Sits right after `music`. No catalogue, a failure or fewer than 4 songs: no row |
| `films` | Films for you | Films from the pool, topped up |
| `tv` | TV shows for you | TV from the pool, topped up |
| `books` | Books for you | Books from the pool, topped up |
| `new` | New and notable | Films and TV from last year on (`filter.release_year.min`), steered by the signals; popular ones for the country when there are none |
| `popular_<country>` | Popular in India | Films and TV with `filter.release_country` and a high popularity floor |
| `throwback` | Throwback: your teens | Era window from birth year (only if set) |

- Each row holds `FEED_ROW_SIZE` (12) items. **An item appears in at most one row**, and the hero isn't repeated.
- A row with fewer than 4 items is dropped.
- **Adding a row must not require changes to the workflow or the API.**

**Cards** show the thumbnail (or the gradient fallback), title, type chip, year, a one-line reason, and hover or long-press actions: ♥ like, 🔖 save, ✕ not interested. A tap opens the **detail view**.

**Detail view** (a sheet on phones, a side drawer on desktop):
- big image, title, year, type, description (from Qloo properties when present), tags;
- **Why you're seeing this:** the reason and the signal chain ("Because you liked The Strokes → Qloo affinity 0.82");
- **Where to find it:** platform buttons (see below);
- **More like this:** an insights call with this item as the signal. For a song it's **"After this song"**: Qloo's artists for the song's artist, one top song each;
- for an artist, **their top songs** from the song catalogue;
- an optional **Preview** button: a song's iTunes preview, or for other items a YouTube video looked up on demand.

### Platform links (`domain/links.py`)

A pure function turns `(title, entity_type, year, country_code, external_ids, isbn13)` into an ordered list of `{ platform, label, url, kind: "direct" | "search" }`.

| Type | Links, in order |
|---|---|
| Artist (and song favourites) | YouTube (top songs search), Spotify search, YouTube Music search, Apple Music search |
| Song card | Apple Music (direct, the store link iTunes gave), YouTube search, Spotify search, YouTube Music search, each for "title + artists" |
| Film | JustWatch search for the user's country (shows Netflix, Prime Video, JioHotstar and the rest), Netflix search, Prime Video search, YouTube trailer search |
| TV show | Same as film |
| Book | Google Books (ISBN when present), Goodreads search, Amazon search, Open Library |

- If Qloo gives an external ID we trust (for example IMDb or Spotify), add a **direct** link first.
- URLs are built with proper encoding. Never put a key or personal data in a link.
- The primary button is the first link. The rest go in a "More places" menu.

### Thumbnails
- Artists, films and TV: Qloo `properties.image.url` (the adapter must parse it; check the shape with `scripts/qloo_smoke.py`).
- Books: Open Library cover from `isbn13`, otherwise the fallback.
- Songs: the iTunes artwork URL (square).
- Fallback: a gradient tile in the type's colour with its icon and the title.
- Use `loading="lazy"`, fixed aspect ratios (posters 2:3, artists 1:1, books 2:3) and a blur-up placeholder, so rows never jump.

### The agent (`application/agent/`)

There is **one agent, built as a hybrid**:
- fixed LangGraph workflows where **code controls the order**;
- one **research step** where the AI decides its own Qloo calls (LangChain `create_agent`).

**Tools** (`agent/tools/`). Each is a thin wrapper over a port, and every call is logged.

| Tool | What it does |
|---|---|
| `search_entities(name, type?)` | Qloo `/search`. Returns matches with type, year and image |
| `find_tags(query)` | Qloo `/v2/tags` |
| `get_insights(type, signals, tags?, era?, country?, popularity_min?, take)` | Qloo `/v2/insights`. **Always adds the profile's exclusions itself**, allows only supported parameters, and drops book signals for other types (Qloo rejects them) |
| `find_journal_links(query, kind?)` | Existing items and places already linked in this profile's journal |
| `compare_tastes(group_a, group_b)` | Qloo `/v2/insights/compare` (taste page and "Taste match", Phase 4) |
| `submit_candidates(...)` / `propose_matches(...)` / `propose_links(...)` | The agent's final, structured answer |

**Limits** (LangChain middleware on `create_agent`):
- `ToolCallLimitMiddleware`: at most 12 Qloo calls in the research step, 5 searches per favourite, and 10 per journal entry.
- `ModelCallLimitMiddleware`: at most 8 model calls per run.
- `ToolRetryMiddleware` for temporary errors.
- `ModelFallbackMiddleware`: switches to the Groq fallback model when a Gemini call fails or times out.
- A 25-second overall timeout.
- Row top-ups are code, not agent calls, and count toward a per-feed budget of `FEED_MAX_QLOO_CALLS` (24), most of them served from `qloo_cache`. The rows get whatever research and the fallback left unspent (`qloo_calls` in the state).

When a limit is hit or the agent fails, the **rule-based fallback** takes over, so a feed is always produced.

#### Workflow 1: build the feed (`workflows/build_feed.py`)

| # | Step | Who decides |
|---|---|---|
| 1 | `load_context`: profile, verified favourites, feedback totals, exclusions, learned weights, confirmed journal signals | Code |
| 2 | `research`: the agent gets the brief (your signals, what you've been liking lately, country), asks Qloo for each type, then submits its 12 best "featured" picks. Every Qloo result joins the pool | **AI agent** |
| 3 | `fallback`: runs only if research failed, hit a limit or returned too few. Fixed queries per type, relaxed up to 2 times (drop the popularity floor, widen to tags) | Code |
| 4 | `build_rows`: pick the hero (the agent's best featured pick with an image), then each registered row takes from the pool or runs its fixed queries within the budget, ranked by Qloo affinity, then learned weight, then popularity | Code |
| 4b | `add_songs`: the "Songs for you" row from the song catalogue, for the artists already in the feed | Code |
| 5 | `guardrails`: remove excluded items, require a source on every item, dedupe across rows, drop short rows | **Code only** |
| 6 | `decorate`: reasons (from the signal behind each pick), images, platform links, taste tags | Code |
| 7 | `explain`: a "what changed since last time" summary (the first feed uses a template) | AI, with a template fallback |

#### Workflow 2: resolve a favourite (`workflows/resolve_favourite.py`)

The user can type a name, a song title, a remembered lyric or a description. The agent climbs the **hint ladder** and stops at the first good match:
1. **Interpret the input:** the AI guesses the song, singer, composer, film and year.
2. Search Qloo for the **singer**.
3. Try **spelling variants**.
4. Search the **composer or music director**.
5. Search the **film** the song comes from.
6. Search the film's **lead actor**.
7. Use a **genre or region tag** as the signal.
8. **Ask the user** for a hint: singer, film or year.
9. Otherwise **keep it as text**. It still shows on the taste page, but it isn't a Qloo signal.

Rules for this workflow:
- **Never search Qloo for lyrics or song titles.** Qloo has no songs.
- Accept a match only after checking its **type, year and name**, not just that the result isn't empty.
- Return up to 3 proposals.
- **The user confirms** a proposal before it's saved as a verified favourite. Only verified favourites become Qloo signals.

#### Workflow 3: link a journal entry (`workflows/link_journal.py`)
1. **Extract mentions** (LLM, structured output): artists, songs, films, TV shows, books, places and a mood.
2. **Resolve songs, artists, films, TV shows and books** with the hint ladder from Workflow 2.
3. **Match places** and earlier mentions to existing journal nodes with `find_journal_links`, or propose new ones.
4. **Return suggested links**, each with a short reason. The user confirms each one with ✓ or ✗.

Confirmed media links become taste signals (weight as a like) and feed the "From your journal" row.

#### For all workflows
- **Every tool call and decision goes into the agent log** in plain English. For example: "Asked Qloo for films like The Strokes → 10 found. Dropped 2 you said you're not interested in."
- The log is saved in `agent_runs` and shown in the UI (a slide-out "How this feed was built" panel).
- Nodes and tools depend on ports only. The workflow builders inject them.
- The research agent compiles to a LangGraph graph, so it runs as one node inside the outer workflow.

### Row strategies (`application/rows/`)
- `FeedRow` has two methods:
  - `applies(context)`: whether the row should exist for this profile (for example `throwback` needs a birth year);
  - `specs(context, pool)`: the rows it makes, each a `RowSpec` with its fixed Qloo queries, which research results it may take, its order and its minimum size.
- `build_rows` fills every spec the same way. Rows register in `RowRegistry` with an order.
- Items the user already loves are never recommended back to them.

### Cold start
Qloo needs no history. The first feed uses whatever you give:

| You give | The research brief and fallback use |
|---|---|
| **3 or more favourites** | The favourites as signals. Qloo expands them straight away |
| **1–2 favourites** | Those, plus the taste quiz picks, plus country |
| **Nothing** (skipped) | The taste quiz picks, country and a high popularity floor. Never artists from the age signal alone (it returns generic bands) |

**Onboarding** (one screen per step, with progress dots and Skip):
1. Your name.
2. Country (optional) and birth year (optional).
3. Pick favourites: a search box with type chips (Music, Films, TV, Books) and image results; tap to add, aim for 3+.
4. **Taste quiz ("this or that")**: two big image cards at a time, `QUIZ_PAIRS` (6) rounds. Each tap is a `liked` signal at quiz weight. The next pair has the unseen item most similar to the last pick (Qloo scores the set with `filter.results.entities`), plus one different item to keep exploring. The card not chosen gets no signal.
5. "Building your feed…" with the live agent log, then the dashboard.

### Learning rules (`domain/policies.py`)

| Signal | Effect |
|---|---|
| `liked` (♥) | +1.0 |
| `saved` (🔖) | +0.6 |
| `opened` (tapped a platform link) | +0.3, at most once per item per day |
| `quiz_pick` | +0.5 |
| `journal_confirmed` | +1.0 |
| `disliked` (👎 in the detail view) | −0.5 (lowers ranking only) |
| `not_interested` (✕) | Exclude the item (reversible in Settings) |

**Feedback into Qloo**
- Items with a total weight ≥ 0.6 become Qloo signals next time, alongside verified favourites. The newest strong signals come first, so the feed follows your recent taste.
- Excluded items go into `filter.exclude.entities`, and the guardrails remove them again.
- **Songs:** Qloo has no songs, so liked, saved, opened and disliked on a song also count for its artist. "Not interested" in a song hides only that song; excluding an artist hides their songs too.

**Ranking:** Qloo affinity first, then learned weight, then popularity.

These are simple heuristics. Describe them as that.

### Journal

**Entries**
- An entry has a date, text and optional mood. Write it, or tap the mic and **speak**: the browser records, `POST /journal/transcribe` (the raw recording as the body) returns text through Groq Whisper, and the user edits it before saving. Audio is discarded.
- The editor reminds the user that entries are private and never shared.

**Links**
- Saving an entry starts `link_journal`. Suggestions show as chips under the entry ("Interstellar · film", "Arctic Monkeys · artist") with ✓ and ✗, plus "Confirm all".
- Each link has a **kind** (`mentions`, `because_of`, `liked`, `related`), a **source** (`user`, `agent`, `qloo`, `feed`) and a **status**: `suggested`, `confirmed` or `rejected`. A rejected suggestion is never suggested again.
- Suggested links appear only in the suggestions area. Only confirmed links affect the feed, the taste page and the taste map.

**Views**
- The **journal timeline**: entries by day, with the confirmed items as small thumbnails.
- An **entry page** with its linked items (each opens the detail view).
- The **taste map** (on the taste page): favourites, liked items and journal items as nodes, with `because_of` and `mentions` links, capped at `TASTE_MAP_MAX_NODES` (40) and coloured by type. A list view is always available.

**Storage:** two Postgres tables, `journal_nodes` (entries, media items, places) and `journal_links`.

### Taste page
- **Your taste in a sentence** (LLM, template fallback), built only from tag names and titles.
- Top tags and genres, from the tags on your favourites and liked items (and Qloo `compare` where it helps).
- Your favourites and liked items as an image grid, with remove and undo.
- The taste map.
- "Not interested" list with undo lives in Settings.

---

## Design system

**Layout** from the reference mockup (`image.png`): sidebar, search bar, hero banner, category tiles, rows, right rail. **Look** inspired by yuzuhire.com: light, airy, premium. **Every screen must look finished.** No unstyled default components.

**Design skills are compulsory for frontend work.** The repo ships them in `.claude/skills/`:
- `impeccable` (Paul Bakaus): run `/impeccable init` once to write `PRODUCT.md` and `DESIGN.md`; use `shape` before a new screen, then `critique`, `audit` and `polish` before every frontend PR;
- `emil-design-eng`, `animate`, `review-animations`, `improve-animations` and `break-ui` (Emil Kowalski): use `animate` for every transition, `review-animations` on every PR that adds motion, and `break-ui` on cards, rows and the detail sheet.
When a skill and this file disagree on tokens, this file's tokens win; for craft (spacing, hierarchy, motion feel), follow the skills.

**Fonts** (Fontshare, `https://api.fontshare.com/v2/css?f[]=switzer@400,500,600,700&f[]=chillax@500,600,700&display=swap`)
- **Chillax** 600 for the brand, hero titles and row titles, letter-spacing −0.03em.
- **Switzer** 400–700 for everything else.

**Colour tokens** (Tailwind theme and CSS variables in `app/theme`)

| Token | Value | Use |
|---|---|---|
| `ink` | `#1A1A1A` | Headings, primary text, dark buttons |
| `body` | `#444444` | Body text |
| `muted` | `#6B6B6B` | Secondary text |
| `surface` | `#FFFFFF` | Page |
| `surface-2` | `#F5F5F5` | Panels, card backs |
| `line` | `#E0E0E0` | Borders (`#0000000F` for hairlines) |
| `primary` | `#E8A838` | Primary buttons, active tabs, focus ring (hover `#D4952E`) |
| `brand` | `#FFC700` | Logo and brand accents only |
| `music` | `#E8A838` | Music chip and fallback gradient |
| `film` | `#E0594A` | Film chip |
| `tv` | `#4A7BE0` | TV chip |
| `book` | `#3E9C6B` | Book chip |

**Shapes and effects**
- **Sidebar:** white, hairline right border, active item an amber-tinted pill (`#E8A838` at 14%) with ink text and an amber icon.
- **Top bar:** sticky, glass (`backdrop-filter: blur(16px)`, white at 85%), a rounded search field (radius 10px, `surface-2` fill).
- **Hero banner:** rounded (16px) image banner of the top pick with a dark-to-transparent gradient from the left, white Chillax headline with one word in amber, a primary button.
- **Category tiles:** image tiles (radius 12px) with a bottom gradient, title and one-line description, a round arrow button. The tile image is the image of the top feed item of that type (rule 13: no stock photos are stored); the fallback is the type's gradient.
- **Right rail cards:** white panels (radius 12px, hairline border); mood chips are pill toggles (selected = amber fill, ink text).
- Buttons: radius 8px, `0.7rem 1.6rem` padding, lift 1px on hover. Primary is amber with ink text; secondary is white with a `#DDD` border.
- Cards: radius 10px, `0 2px 12px #0000000F` shadow, scale 1.03 and show actions on hover.
- Panels and drawers: white, radius 12px, hairline border.
- Motion: 150–300 ms ease-out. Respect `prefers-reduced-motion`.
- Dark mode is a stretch goal; build with tokens so it's a theme swap.

**Rows** scroll horizontally with snap, arrow buttons on desktop, and swipe on phones. Show skeleton cards while loading.

---

## Qloo reference

The full notes are in `docs/QLOO_NOTES.md`.

**Calling it**
- Base URL: `https://hackathon.api.qloo.com`. The hackathon key returns 401 on any other host.
- Send the key in the `X-Api-Key` header.
- Every call is a GET with query parameters.

**Endpoints**
- `/search`: turns names into entity IDs (with images and properties).
- `/entities`: gets details for IDs.
- `/v2/insights`: recommendations. `filter.type` is required.
- `/v2/tags`: tag IDs.
- `/v2/insights/compare` and `/v2/analysis/compare`: both work (checked live) and return tags, not items.
- **Never call `/recommendations` or `/recs`.**

**Entity types we use:** `urn:entity:artist`, `movie`, `tv_show` and `book`.
- Qloo has **no song type and no lyrics**. Qloo's music picks are artists; their link opens the artist's top songs. Song cards come from the song catalogue for those artists (see "Songs" in the tech stack). Never search Qloo for a song title or a lyric.

**Parameters we use**
- `signal.interests.entities`
- `signal.interests.tags`
- `filter.release_year.min` and `.max` (movies and TV)
- `filter.publication_year.min` and `.max` (books)
- `filter.release_country` (films and TV; it needs the full country name, which the adapter converts from the ISO code)
- `filter.popularity.min`
- `filter.exclude.entities`
- `filter.exclude.tags`
- `filter.results.entities`: scores a given set, used by the taste quiz (checked live: it works).
- `take`: the default is 20 (up to 50), so **always set it**.

**Gotchas**
- **Invalid parameters are silently ignored.** When results are empty, check the parameter guide.
- **Some entities and regions have little data.** Follow the hint ladder, logging each step.
- Cache responses on the server (`qloo_cache` table), **never in the repo**.

---

## Media preview (YouTube, optional)

- Only when the user taps **Preview** in the detail view. The feed never calls YouTube.
- The default quota is about **100 searches a day**, so cache every lookup in `media_cache`.
- Before using a video, call `videos.list` to check that `status.embeddable` is true, and read `contentDetails.duration`. Skip Shorts (under 90 seconds or `#shorts` in the title).
- If nothing fits, hide the Preview button for that item. **Never substitute an unrelated video.**
- Without `YOUTUBE_API_KEY`, the Preview button is hidden.

**Song previews (iTunes).** A song card's `preview_url` is Apple's 30-second preview. Apple's Search API terms shape how it's used:
- it plays only on tap, streamed and never downloaded, saved or cached (we keep the URL, never the file);
- it's shown next to the song's Apple Music link and credited "Previews courtesy of iTunes";
- artwork and previews are only used to promote the song.

---

## LLM rules

- Everything goes through the `LanguageModel` port. `infrastructure/llm/factory.py` builds the chat model for a provider name (`groq` or `gemini`), and `api/deps.py` is the only place that picks them. Provider, model and key come from the environment.
- **Gemini is the main model, Groq the fallback** (switched 24 Oct). Groq's free tier allows only 8,000 tokens a minute, which a feed build can exceed; Gemini's free tier is far roomier. A Gemini call that fails or times out (15 seconds) is retried once on Groq (8 seconds). If that also fails, the template fallback takes over.
- The LLM never decides *what* is recommended: every pick comes from Qloo (rule 1). So the model's own knowledge cut-off doesn't matter; speed, limits and reliable tool calls do.
- **Journal text never goes to Gemini on a free key**, because free-tier prompts can be used for training. `link_journal` and transcription use the Groq model and key explicitly (not the main model), and a Groq failure means "no suggestions, try again". Lift this only with a paid Gemini key.
- Validate output against Pydantic schemas. On invalid output, fall back to templates.
- Use a low temperature for research, and a 15-second overall timeout per LLM step that triggers the template fallback.
- Send only what's needed:
  - first name, country, favourites and liked titles;
  - the text of a journal entry, only while suggesting links for it.
- Never send keys or other personal data.
- Put a spending cap on the account, and rate-limit feed builds per user.

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
- Domain errors return `{ "error", "detail" }` with status 404, 409, 422, 429 or 502.
- Never put stack traces in responses.

**Keeping in sync**
- Update `docs/API_CONTRACT.md` in the same PR as any endpoint change.
- Regenerate the frontend types (`npm run gen:api`) after any endpoint change.

---

## Frontend conventions

**Structure**
- One folder per feature in `src/features/<name>/`. Pages only compose features.
- Design-system components (Button, Chip, Card, Row, Sheet, Skeleton, Sidebar, TopBar, HeroBanner, CategoryTile, RailPanel) live in `src/shared/ui/` and use the tokens. Features never hard-code colours.
- Run the design skills (see "Design system") on every frontend task, and paste the `critique` / `review-animations` summary into the PR description.
- Use TanStack Query for server state only. Don't add a global store unless the team agrees.
- Call the API only through `src/shared/api`, which is typed from the generated schema.

**UX**
- Phone first (360 px), then tablet and desktop (rows show 2.3, 4.5 and 6.5 cards).
- Tap targets of at least 44 px; body text at least 16 px; contrast at least WCAG AA.
- Everything works from the keyboard; rows are focusable lists; the detail sheet traps focus and closes on Escape.
- `aria-live` on the agent log and on feed refresh toasts.
- Optimistic updates for like, save and not interested, with an Undo toast.

**States and badges**
- Always show loading (skeletons), empty and error states, each designed, not plain text.
- Recommendations show a "Demo data" or "Live Qloo" badge, and song cards "Song via iTunes".

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

## Commands

```bash
# backend (uv reads .python-version and uses Python 3.12)
cd backend && uv sync                  # creates .venv and installs everything from uv.lock
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs
uv run ruff check . && uv run ruff format --check .
uv run alembic upgrade head
uv add --bounds exact <package>        # add a dependency (--dev for dev tools)

# frontend
cd frontend && npm install
cp .env.example .env.local             # once; sets VITE_API_BASE_URL
npm run dev                            # http://localhost:5173
npm run build && npm run lint
npm run gen:api                        # regenerate API types from the backend's /openapi.json
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
- YouTube (optional preview): `YOUTUBE_API_KEY`
- Songs (iTunes, no key): `SONGS_ENABLED=true`
- LLM:
  - `LLM_PROVIDER`
  - `LLM_MODEL`
  - `LLM_API_KEY`
  - `LLM_FALLBACK_PROVIDER`
  - `LLM_FALLBACK_MODEL`
  - `LLM_FALLBACK_API_KEY`
  - `STT_MODEL=whisper-large-v3-turbo`
- Agent and limits:
  - `AGENT_MAX_TOOL_CALLS=12`
  - `AGENT_MAX_MODEL_CALLS=8`
  - `AGENT_TIMEOUT_SECONDS=25`
  - `FEED_MAX_QLOO_CALLS=24`
  - `RESOLVE_MAX_SEARCHES=5`
  - `LINK_MAX_SEARCHES=10`
  - `AGENT_MAX_RETRIES=2` (fallback relaxations)
  - `FEED_RATE_LIMIT_PER_HOUR=20`
- Feed, quiz and taste map:
  - `FEED_ROW_SIZE=12`
  - `QUIZ_PAIRS=6`
  - `TASTE_MAP_MAX_NODES=40`

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

**A feed row**
1. Add `application/rows/<name>.py` implementing `FeedRow`.
2. Register it with its order.
3. The feed shows it with no other changes.

**An agent step**
1. Add a node in `application/agent/nodes/` that does one job and writes to the log.
2. Wire it into the workflow in `application/agent/workflows/`.

**An agent tool**
1. Add it in `application/agent/tools/` as a thin wrapper over a port. Validate its inputs and log every call.
2. Add it to the tool list of the workflow that needs it.

**A platform**
1. Add it to the table in `domain/links.py`, with its URL template and label.

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
3. Add designed loading, empty and error states.

---

## Definition of done

- Merged into `main`.
- Working locally at phone and desktop width, matching the design system.
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
- Run the relevant checks: `ruff` for the backend, `lint` and `build` for the frontend.
- Report the results honestly. Never say a check passes without running it.

**Always**
- Never commit secrets or real Qloo data.
- If you're unsure about a Qloo parameter or response shape, check `docs/QLOO_NOTES.md`. If it's still unclear, say so instead of guessing.
