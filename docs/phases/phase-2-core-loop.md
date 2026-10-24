# Phase 2: Feed and the new frontend

**Dates:** Sat 24 – Mon 26 Oct · **Hours:** about 16 each · **Previous:** [Phase 1](phase-1-foundations.md) · **Next:** [Phase 3: Journal and taste page](phase-3-memory-graph.md)

**Goal:** the new product works end to end locally.
- Onboarding: name, optional country and birth year, favourites with image search, the "this or that" taste quiz.
- The home **feed**: a hero and rows with thumbnails, reasons and platform links.
- The **detail view**: why, where to find it, more like this.
- **Feedback** (like, save, open, not interested) changes the next feed, and the log says why.
- A brand-new frontend on the new design system.

**Before you start:** read `docs/PLAN.md` section 0 (the pivot), then `CLAUDE.md`: "The feed", "Platform links", "Thumbnails", "Row strategies", "Learning rules" and "Design system".

> This file replaces the old Phase 2 (sessions, caregiver review, player, Person mode). That code was merged on `Developers/gg`; this phase refactors the backend and replaces the frontend.

---

## First: agree the contract (all three, 30 minutes, Saturday night)

The full shapes are in `docs/API_CONTRACT.md`, "Phase 2: the feed".

| Route | Request | Response |
|---|---|---|
| `GET /api/v1/profiles/{id}/feed` | nothing | `Feed`, or `404` if none yet |
| `POST /api/v1/profiles/{id}/feed/refresh` | nothing | `202`, `Feed` with `status: "building"` |
| `GET /api/v1/agent-runs/{id}` | nothing | `AgentRun` (kind `feed`) |
| `GET /api/v1/profiles/{id}/items/{ref}` | nothing | `ItemDetail` |
| `POST /api/v1/profiles/{id}/items/{ref}/preview` | nothing | YouTube video, or `404` |
| `POST /api/v1/profiles/{id}/feedback` | `{ ref, title, entity_type, signal, platform? }` | `{ ok, counted, effect, stale }` |
| `GET /api/v1/profiles/{id}/library` | nothing | `{ liked, saved }` |
| `GET` / `DELETE /api/v1/profiles/{id}/exclusions…` | — | the not-interested list, with undo |
| `POST /api/v1/profiles/{id}/quiz/next` | `{ picked_ref?, shown_refs }` | `{ pair, round, rounds, done }` |

Phase 1 changes: `birth_year` becomes optional (1900 to the current year); `Favourite` and taste search results gain `image_url`.

**Removed routes:** `/sessions/**`, `/history`, `/shelf`, `/warmup/next`, `/person-signals`, `/reactions`, and the old exclusion `POST`.

---

## Agent: images, the feed workflow, rows, quiz scoring (≈ 16 h)

### Agent 1. Check images and external IDs (Saturday night, first hour)
- Extend `scripts/qloo_smoke.py`: 10 entities per type through `/search` and insights.
- Record in `docs/QLOO_NOTES.md`, section 6: the image field's shape and how often it's present per type, and what `external` holds. **Field names and percentages only.**
- If images are rare for a type, tell Frontend now, so the fallback tile gets more design time.

### Agent 2. Images, external IDs, ISBN and tags in the adapters
- `EntityMatch` gains `image_url`, `external` (a small dict of trusted IDs), `isbn13`, `description` and `tags` (names, up to 4).
- Live adapter: parse them from `/search` and insights. Fixture adapter: add the fields to the fixtures (`image_url: null`).
- Contract tests with `httpx.MockTransport` for each field, including missing ones.

### Agent 3. Stub feed (Sunday by noon)
A fixture-backed `build_feed` that returns a `Feed` in the real shape (hero plus 5 rows), so Frontend can build against it.

### Agent 4. The `build_feed` workflow
- Rename and reshape `workflows/plan_session.py` into `workflows/build_feed.py`, following `docs/AGENT.md`, section 3.
- **Keep:** `load_context` (now loads exclusions, learned weights and the previous feed's refs), `research` and `research_agent.py` (new brief and prompt), `fallback` (per type), the tools, the middleware and the log.
- **New nodes:** `build_rows`, `rank`, `decorate`, `explain`.
- **Remove:** `select_items`, `resolve_media`, `compose`, and the session-length part of `guardrails`.
- Guardrails: exclusions, source required, dedupe across the feed, drop rows under 4 (see `AGENT.md`, section 9).

### Agent 5. Row strategies (`application/rows/`)
- `FeedRow` (`applies`, `queries`, `select`) and `RowRegistry`, replacing `application/modes/`.
- Rows: `for_you`, `cross_culture` (right rail, one per type: Watch, Read, Listen), `because_<ref>` (up to 2), `music`, `films`, `tv`, `books`, `popular_<country>`, `throwback`. (`journal` comes in Phase 3.)
- Also compute `taste_tags` (up to 8 tag names from favourites and strong signals) for the sidebar chips.
- The per-feed budget `FEED_MAX_QLOO_CALLS` (24) is shared and enforced in code.

### Agent 6. `explain` with templates
- One LLM call writes reasons (≤ 12 words each) and the "what changed" summary from item titles, signal titles and the previous feed's tags.
- Templates: "Because you liked X", "Popular in India right now", "A favourite in your taste".
- Guardrail: a reason over 120 characters, or naming another item, is replaced by its template.

### Agent 7. Quiz scoring
- Reuse the warm-up scoring in `TasteService.score` (`filter.results.entities`) for the taste quiz: the unseen item most like the pick, plus one of another type.
- The quiz set: about 16 popular, varied items for the country (films and TV with `filter.release_country`, artists from those films, a few popular books), cached per country.

### Agent 8. Demo profiles
Hand-written fixtures, all `"demo": true`:
- **Aanya** (India): indie and alt rock, sci-fi films, a few likes, one not-interested item.
- **Leo** (US): classic films and jazz, a couple of books.

### Agent 9. Tests
- Each node with a scripted fake model; research stops at its limits and the fallback still gives a feed.
- Each row strategy: `applies`, its query, its selection.
- Guardrails: an excluded item never appears in any row or the hero; an item appears once; every item has a `source` and a `reason`.
- `get_insights` always applies the exclusions.
- An LLM failure in `explain` falls back to templates.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("The feed", "The agent", "Row strategies") and docs/AGENT.md
(sections 3, 7, 8, 9). Refactor workflows/plan_session.py into workflows/build_feed.py:
keep load_context, research (new brief and system prompt per AGENT.md section 10),
fallback per type, tools and middleware; add nodes build_rows, rank, decorate, explain;
remove select_items, resolve_media, compose and the session-length guardrail. Replace
application/modes/ with application/rows/ (FeedRow: applies, queries, select; RowRegistry
with order) and the rows for_you, because_<ref> (max 2), music, films, tv, books,
popular_<country>, throwback, sharing FEED_MAX_QLOO_CALLS. Guardrails: exclusions,
source required, dedupe across hero and rows, drop rows under 4. explain writes reasons
and a summary with a template fallback. Tests with a scripted fake model for every
node, row and guardrail. Run ruff and pytest.
```

**Check:** with fixtures, `build_feed` for Aanya returns a hero and at least 5 rows, no repeats, every item with a reason, and the log reads well.

---

## Backend: feed storage, links, feedback, quiz, cleanup (≈ 16 h)

### Backend 1. Migration
- New: `feeds` (`id`, `profile_id`, `status`, `stale`, `agent_run_id`, `hero` JSONB, `rows` JSONB, `summary`, `created_at`).
- `profiles.birth_year` becomes nullable (the 1900 floor stays).
- Drop `sessions` and `session_items`. Keep `feedback`, `exclusions`, `agent_runs`, `qloo_cache` and `media_cache`.
- `feedback` gains the new signal names (`liked`, `saved`, `opened`, `quiz_pick`, `disliked`, `not_interested`, and later `journal_confirmed`); its `actor` column goes.
- In-memory and Postgres repositories for feeds.

### Backend 2. Platform links (`domain/links.py`)
- A pure function from `(title, entity_type, year, country_code, external, isbn13)` to `PlatformLink[]`, per `CLAUDE.md`, "Platform links".
- URL templates (search pages; check each one by hand once):
  - YouTube `https://www.youtube.com/results?search_query=<artist>+top+songs`
  - Spotify `https://open.spotify.com/search/<q>`
  - YouTube Music `https://music.youtube.com/search?q=<q>`
  - Apple Music `https://music.apple.com/search?term=<q>`
  - JustWatch `https://www.justwatch.com/<country>/search?q=<q>` (lower-case ISO code, `us` by default)
  - Netflix `https://www.netflix.com/search?q=<q>`
  - Prime Video `https://www.primevideo.com/search/ref=atv_nb_sug?phrase=<q>`
  - Google Books `https://www.google.com/search?tbm=bks&q=isbn:<isbn>` or by title
  - Goodreads `https://www.goodreads.com/search?q=<q>`
  - Amazon `https://www.amazon.<tld>/s?k=<q>` (`.in` for India, `.com` otherwise)
  - Open Library `https://openlibrary.org/search?q=<q>`
- Direct links only for external IDs Agent 1 confirms (for example IMDb `https://www.imdb.com/title/<id>/`).
- Unit tests: encoding (spaces, `&`, non-Latin titles), labels ("Search on …" vs "Watch on …"), country handling.

### Backend 3. Learning rules (`domain/policies.py`)
- Weights from `CLAUDE.md`, "Learning rules". `opened` counts once per item per day.
- `not_interested` creates an exclusion; deleting the exclusion undoes it.
- Strong signals (total ≥ 0.6), newest first, are what `load_context` passes to research.
- Unit tests for every weight and the once-a-day rule.

### Backend 4. `FeedService`
- `get_latest(profile)`, `refresh(profile)` (starts a run in the background, returns the building feed; reuses a running build), rate limit per user.
- After feedback: mark the latest feed `stale`; for `not_interested`, also remove the item from the snapshot at once.
- `item_detail(profile, ref)`: the item (from the feed, the library or `/entities`), description, links, and `more_like_this` (one cached insights call, exclusions applied).

### Backend 5. `FeedbackService`, library and exclusions
- `POST /feedback` with the signals in the contract, returning a friendly `effect`.
- `GET /library` (liked and saved, newest first) and the exclusions list with undo.

### Backend 6. `QuizService`
- `next(profile, picked_ref, shown_refs)` per the contract. Each pick stores `quiz_pick`.
- Rewrite of `services/warmup.py`; the shelf goes.

### Backend 7. Optional preview
`POST /items/{ref}/preview` uses the existing YouTube resolver (with the Shorts filter) and `media_cache`. `preview_available` is false without `YOUTUBE_API_KEY`.

### Backend 8. Cleanup
- Remove the sessions, shelf, person and reactions routes, services, schemas and repositories, and their tests.
- Remove `domain/sessions.py`, `domain/media.py` (keep only what the preview needs), `BOOK_TALK_SECONDS`, `WARMUP_PAIRS`, `SESSION_TARGET_MINUTES` and `MEMORY_GRAPH_MAX_NODES`. Add the new settings from `CLAUDE.md`, "Environment variables", to `.env.example`.
- The demo seed creates Aanya and Leo with their favourites, likes and one exclusion, then builds their first feed.

### Backend 9. Routes and tests
- Every route in the contract, with ownership checks (`404` for someone else's).
- API tests: cross-user access is denied; feedback marks the feed stale; not-interested disappears from the snapshot at once and from the next feed; the quiz's pairs follow the rules; the rate limit; `birth_year` optional.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("The feed", "Platform links", "Learning rules") and docs/API_CONTRACT.md
("Phase 2: the feed"). Add an Alembic migration: feeds table (hero and rows as JSONB,
stale flag), nullable profiles.birth_year, drop sessions and session_items, new feedback
signals without actor. Add domain/links.py (pure, URL-encoded, honest labels, per-country
JustWatch and Amazon) with unit tests. Update domain/policies.py weights. Implement
FeedService (latest, refresh in the background with rate limit, stale marking, instant
removal on not_interested, item_detail with more_like_this), FeedbackService, library,
exclusions with undo, QuizService (rewrite of warm-up), and the optional preview route.
Remove the sessions, shelf, person and reactions code and tests. Seed Aanya and Leo.
API tests for ownership, stale, exclusions, quiz and rate limit. Run ruff and pytest.
```

**Check:** every Phase 2 route works in `/docs` against the seeded demo profiles.

---

## Frontend: design system and every screen, from scratch (≈ 16 h)

Start a new frontend tree. Keep only the toolchain (Vite, TypeScript, Tailwind, ESLint, Prettier), `shared/api/client.ts`, `shared/api/supabase.ts`, the generated schema and `shared/data/countries.ts`. Delete the old `features/*`, `pages/*`, layouts and `shared/ui/*`.

**Proposed dependencies (ask the team first, rule 15):** the Fontshare stylesheet (no package); optionally `framer-motion` for the sheet and card motion. Without it, use CSS transitions.

**Design skills (compulsory, in `.claude/skills/`; start a new Claude Code session so they load):**
1. `/impeccable init` once: it writes `PRODUCT.md` and `DESIGN.md` from this product. Feed it `CLAUDE.md`'s "Design system" and the mockup `image.png`.
2. `/impeccable shape <screen>` before each new screen.
3. Use `animate` (Emil) for every transition: card hover, sheet open, quiz pair swap, row refresh.
4. Before each PR: `/impeccable critique`, `/impeccable audit`, `/impeccable polish`, `review-animations`, and `break-ui` on cards, rows and the sheet. Paste the summaries into the PR.

### Frontend 1. Design system (Sunday by noon)
- Tokens from `CLAUDE.md`, "Design system", as CSS variables and the Tailwind theme (`app/theme`). Chillax and Switzer.
- Components in `shared/ui/`: `Button` (primary, secondary, ghost, icon), `Chip` (type chips in their colours, tag chips, mood toggles), `Badge` ("Demo data" / "Live Qloo"), `Sidebar`, `TopBar` (with search), `HeroBanner`, `CategoryTile`, `RailPanel`, `Card` (poster and square, heart button), `FallbackTile`, `Row` (title, subtitle, "See all", horizontal scroll, snap, arrows, keyboard), `Sheet` (bottom sheet on phones, right drawer on desktop, focus trap, Escape), `Skeleton`, `Toast` (with Undo), `EmptyState`, `ErrorState`, `ProgressDots`, `BottomTabs` (phones).
- A `/styleguide` page showing every component, for review.

### Frontend 2. Shell and profiles
The layout of the mockup `image.png`, in our light palette:
- **Sidebar:** logo, "Your personal culture companion", nav (Home, Discover, Music, Movies & TV, Books, Journal, Saved, Taste), **Your taste profile** chips from `taste_tags`, a "Keep exploring" nudge.
- **Top bar:** global search (taste search with image results; picking one opens its detail sheet), the profile menu ("Hey, Aanya": switch profile, Settings, sign out).
- Phones: the sidebar becomes `BottomTabs`; the search becomes a search icon that opens a full-screen search.
- Landing page for signed-out users: a full-bleed hero, one-line pitch, **Try the demo** (primary) and **Start fresh** (secondary).
- Netflix-style **profile picker** with avatar initials in the type colours.

### Frontend 3. Onboarding
- Steps with `ProgressDots` and Skip: name → country and birth year → favourites → taste quiz → "Building your feed…".
- Favourites: search with type chips and image results in a grid; picked items fly into a tray; "3 or more works best".
- Quiz: two big image cards, tap one, the next pair slides in; round counter; "Skip quiz".
- Building screen: an animated progress state with the live agent log lines.

### Frontend 4. The feed (home)
- `HeroBanner` with the top pick's image, a headline with one amber word, its reason, the primary platform button and "Why this?".
- `CategoryTile`s: Music, Movies & TV, Books (image = the top feed item of that type), opening Discover filtered by type.
- **Right rail:** "Your vibe today" mood chips (the button is disabled with "Coming soon" until Phase 4), Quick actions (Surprise me in Phase 4; Watch something new and Find a book jump to those rows; Write in your journal in Phase 3), and **Cross-culture picks** from the `cross_culture` row (Watch / Read / Listen).
- **Discover** page: one type at a time (tabs), a grid of that type's items from the feed plus "More like this" from the top picks.
- Rows with `Card`s: thumbnail or `FallbackTile`, title, type chip, year, reason on hover (always visible on touch, under the title).
- Card actions on hover or long press: ♥, 🔖, ✕, all optimistic with an Undo toast.
- "Refresh for new picks" pill when the feed is `stale`; on refresh, rows show skeletons and then swap in, with the summary as a toast.
- "How this feed was built": a slide-out panel with the agent log (`aria-live`).

### Frontend 5. Detail view
- `Sheet` with a big image, title, year, type, tags, description.
- "Why you're seeing this" with the signal chain.
- "Where to find it": the primary platform button and "More places" (opens in a new tab with `rel="noopener noreferrer"`, and sends an `opened` signal).
- "More like this" row. Optional **Preview** button (YouTube IFrame inside the sheet, only on tap).

### Frontend 6. Settings and library
- Profile fields, "Not interested" list with undo, Liked and Saved grids, delete profile.

### Frontend 7. Quality across all screens
- Phone (360 px), tablet and desktop. Rows show 2.3, 4.5 and 6.5 cards.
- Designed loading, empty and error states everywhere.
- Keyboard: rows, cards, sheet. Contrast AA. `prefers-reduced-motion`.
- `npm run gen:api` after the backend contract lands.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Design system", "Frontend conventions", "The feed"), look at
image.png (layout reference only, use our light tokens), and docs/API_CONTRACT.md
("Phase 2: the feed"). Use the impeccable skill (shape first, critique/audit/polish at
the end) and Emil's animate skill for all motion. Rebuild the frontend from scratch,
keeping only the toolchain, shared/api/client.ts, supabase.ts, the generated schema and
countries.ts. Build the design system in shared/ui with the tokens (Chillax + Switzer,
amber primary, sidebar, glass top bar with search, hero banner, category tiles,
right-rail panels, poster and square cards with a gradient fallback tile, horizontal rows with snap and arrows, a sheet that is a bottom sheet on phones and
a drawer on desktop, skeletons, toasts with Undo, designed empty and error states) and a
/styleguide page. Then the shell in the mockup's layout (sidebar with taste chips, top bar
search, bottom tabs on phones), the landing page, the profile picker, onboarding (name, country
and birth year, favourites with image search, the this-or-that quiz, a building screen
with the live agent log), the feed (hero banner, category tiles, right rail with vibe chips, quick actions and
cross-culture picks, rows, optimistic like/save/not interested,
stale pill, refresh, agent log panel), the detail sheet (why, platform links opening in
a new tab with an opened signal, more like this, optional preview) and settings. Phone
first, keyboard accessible, reduced motion respected. Run lint and build.
```

**Check:** the whole flow works on a phone and a laptop, and every screen matches the styleguide.

---

## Exit check (Monday night)

Locally:
1. Try the demo, pick Aanya. The feed opens with a hero and rows, with thumbnails (or designed fallbacks) and reasons.
2. Open a card. "Search on Netflix" (or "Listen on YouTube") opens the right search in a new tab.
3. Like two items and mark one **Not interested**. It vanishes at once.
4. Refresh.

**Done when:**
- The new feed is different, led by what was liked.
- The dismissed item is gone everywhere, including "More like this".
- The summary and the log explain what changed.
- A new profile can onboard with favourites and the quiz and gets a first feed.

## If you miss it

- All three of you work only on this on Tuesday.
- Phase 3 shrinks to typed journal entries and confirmed links (no voice, no taste map).
- **Cut first in this phase:** `throwback` and `popular_<country>` rows, "More like this", the preview.
- **Never cut:** thumbnails or designed fallbacks, platform links, not-interested never returning, a reason on every card, the agent log.
