# The MeloMind agent: design

Owner: the agent owner. Reviewer: the backend owner. This is the design for `backend/app/application/agent/` and
`application/rows/`. It adds detail to `CLAUDE.md` ("The agent", "The feed", "Journal") and never
overrides it. Qloo specifics are in `docs/QLOO_NOTES.md`.

> **Pivot, 24 Oct 2026.** `plan_session` became `build_feed`, session modes became feed row
> strategies, and `link_memory` became `link_journal`. The research step, middleware, fallback and
> agent log carry over unchanged in spirit.

---

## 1. Shape

- **One agent, three workflows**, all sharing one set of tools: `build_feed`,
  `resolve_favourite` and `link_journal`.
- **Hybrid.** Each workflow is a fixed LangGraph `StateGraph` where code sets the order. Only the
  `research` step of `build_feed` is a tool-calling agent (LangChain `create_agent`) that chooses
  its own Qloo calls. It compiles to a graph and runs as one node.
- **Ports only.** Nodes and tools receive `TasteGraph`, `LanguageModel`, `SpeechToText` and the
  repositories from the workflow builder. They never import an adapter.
- **Every run is an `agent_run`** (kind `feed`, `resolve` or `link`) with a status (`running`,
  `done`, `failed`, or `needs_hint` for the resolver) and a plain-English log. The frontend polls
  `/agent-runs/{id}`.
- **A result is always produced.** When the agent fails or hits a limit, code takes over.

## 2. State

Shared by all workflows: `run_id`, `profile_id`, `log` (list of entries), `limits` (counters
for tool calls, model calls and the deadline), `errors`.

**`FeedState`**

| Field | Written by | Holds |
|---|---|---|
| `brief` | start | Signals, recent likes, dismissed items, country, birth year if set |
| `context` | `load_context` | Profile (first name, country, birth year), verified favourites with Qloo IDs, text favourites, feedback totals, `excluded_ids`, `learned_weights`, confirmed journal signals, the previous feed's item refs |
| `pool` | `research`, `fallback` | `{entity_id, name, type, year, popularity, affinity, image_url, external, isbn13, source, signal}` |
| `research_outcome` | `research` | `ok`, `too_few`, `limit_hit`, `timeout`, `skipped` or `error` |
| `fallback_attempts` | `fallback` | 0–2 |
| `qloo_calls` | `research`, `fallback` | Qloo calls spent so far; `build_rows` gets the rest of `FEED_MAX_QLOO_CALLS` |
| `drafts` | `build_rows`, `guardrails` | Ordered rows of candidates |
| `hero` | `build_rows`, `guardrails` | One item |
| `rows`, `hero_item`, `taste_tags` | `decorate` | Cards with reasons, images and links |
| `summary` | `explain` | The "what changed" line |

**`ResolveState`**: `input_text` (never stored after the run), `kind_hint`, `interpretation`
(`song_title`, `singer`, `composer`, `film`, `year`), `steps_tried`, `proposals` (≤ 3),
`question` (when the run ends with `needs_hint`).

**`LinkState`**: `entry_id`, `entry_text` (held in memory for this run only, never logged),
`mentions`, `resolved` (mention → Qloo entity), `node_matches` (mention → existing node), `proposals`.

## 3. Workflow 1: `build_feed`

| # | Step | Reads → writes | Logs (example) | On failure |
|---|---|---|---|---|
| 1 | `load_context` (code) | `profile_id` → `context` | "Loaded Aanya: India, 4 favourites, 6 likes, 1 dismissed." | Profile missing: run `failed` (404 at the API) |
| 2 | `research` (**agent**) | `brief`, `context` → `pool`, `research_outcome` | Each tool call (section 6), then "The agent picked 12 favourites from 40 results after 4 Qloo calls." | Any error, limit or timeout: keep what was found, set the outcome, go on |
| 3 | `fallback` (code) | Runs only if the outcome isn't `ok` or a type has fewer than 6. One `get_insights` per short type with the top signals; relax up to `AGENT_MAX_RETRIES` (2) | "Only 3 books found; ran the rule-based query. Dropped the popularity floor." | Still short: continue; that row may be dropped |
| 4 | `build_rows` (code) | Pick the hero (the best featured pick with an image). Then each `FeedRow` in `RowRegistry` that `applies`: take from `pool`, run its spec's queries within what's left of `FEED_MAX_QLOO_CALLS` after research and the fallback (`qloo_calls`), rank (affinity → learned weight → popularity; items the last feed showed sink within their band) | "Top pick: The Strokes." "Because you liked Arctic Monkeys: 12 picks." | When the budget runs out, a row uses research results only; a short row is left out and the log says so |
| 4b | `add_songs` (code) | `hero`, `drafts` → `drafts`. The first 6 distinct, non-excluded artists in the feed (hero first, main rows in order); 2 top songs each from the `SongCatalog`, in turn, skipping excluded songs and repeated titles; a "Songs for you" draft inserted right after `music`. 8-second deadline for all lookups | "Looked up songs for 6 artists Qloo picked (Two Door Cinema Club, alt-J…) in Apple's catalogue → 12 songs." | No catalogue (`SONGS_ENABLED=false`, or tests), a timeout, or fewer than 4 songs: no songs row, the feed carries on. One artist failing just gives that artist no songs |
| 5 | `guardrails` (**code only**) | See section 9 | "Removed 2 items you're not interested in." "Dropped “TV shows for you”: too few picks left." | — |
| 6 | `decorate` (code) | Reasons from each pick's signal ("Similar to The Strokes, which you love.") or the row's fixed reason; image URL (Qloo, then Open Library by ISBN, else `null`); platform links from `domain/links.py`; taste tags | "Added images for 96 of 96 picks, and where to find each." | Missing image: `null`, the UI shows the fallback tile |
| 7 | `explain` (LLM + template) | Recently liked titles, tags now and last time, counts → one `summary` line. The first feed always uses the template | "More indie rock and sci-fi today, because you liked Foster the People." | Invalid output, a line over 140 characters, or a 15-second timeout: the template |

The feed is saved as a snapshot in `feeds` with its `agent_run_id`. `GET /feed` returns the latest
`done` snapshot, so the home screen never waits for a build.

**Debounced rebuilds.** Feedback marks the feed `stale`. The frontend shows "Refresh for new picks"
and starts a rebuild on tap. A not-interested item is also removed from the current snapshot at once,
so it disappears without waiting.

## 4. Workflow 2: `resolve_favourite` (the hint ladder)

Input: whatever the user typed, plus an optional kind. Stop at the first accepted match.
At most `RESOLVE_MAX_SEARCHES` (5) Qloo searches, so later rungs are skipped when the budget runs
out. A rung with nothing to search (no composer known, say) is skipped without spending a search.

| Rung | Action | Qloo call |
|---|---|---|
| 1 | **Interpret** (LLM, structured): guess song, singer, composer, film, year | none |
| 2 | Search the singer | `search_entities(singer, artist)` |
| 3 | Spelling variants of the singer (initials, spacing, transliteration) | `search_entities` |
| 4 | Search the composer or music director | `search_entities(composer, artist)` |
| 5 | Search the film the song comes from | `search_entities(film, movie)` |
| 6 | Search the film's lead actor | `search_entities(actor, artist)` *(to verify: actors may be `person`)* |
| 7 | A genre or region tag as the signal | `find_tags(query)` |
| 8 | Ask the user for a hint (singer, film or year). Run ends `needs_hint` | none |
| 9 | Keep as text: shown on the taste page, not a Qloo signal | none |

- **Never search Qloo for a song title or lyric.** A lyric is used in rung 1 only, then dropped.
  The log says "Interpreted a lyric hint", never the lyric.
- **Acceptance (code):** the result's type matches the rung's expected type; the name matches
  after normalising case, punctuation and initials; and, when both years are known, the year is
  within 5 years for films and books. An artist with no year passes on name and type.
- **Output:** up to 3 proposals `{entity_id, name, type, year, image_url, rung, why}`. The user
  confirms one, and only then is it saved as a verified favourite.

## 5. Workflow 3: `link_journal`

1. **Extract** (LLM, structured output, Groq only) from the entry text. Schema:
   `mentions: [{ kind, text, year?, confidence }]` plus `mood?`, where `kind` is one of `artist`,
   `song`, `movie`, `tv_show`, `book`, `place`; `confidence` is 0–1. Mentions under 0.5 confidence
   are dropped. People's names are never extracted.
2. **Resolve** songs, artists, films, TV shows and books with the hint ladder (shared budget of
   `LINK_MAX_SEARCHES`, 10, per entry).
3. **Match** places and already-linked items to existing nodes with `find_journal_links`, or
   propose a new node.
4. **Propose links**: `{ target: node_id | new_node {kind, title, year?, qloo_id?, image_url?},
   link_kind: "mentions", evidence }` with `source = agent`, `status = suggested`. Code drops any
   proposal whose `(from, to, kind)` was rejected before. The user confirms each one with ✓ or ✗.

**On confirm** (service code, not the agent): a media node with a Qloo ID gets a
`journal_confirmed` feedback signal (+1.0), and the feed is marked stale.

## 6. Tools (`agent/tools/`)

Each is a thin wrapper over a port. Each validates its inputs and logs its call and result count.
The agent never sees Qloo's long IDs: tools answer with short aliases (`e1`, `e2`…) that
`ToolContext` maps back, because Groq's free tier counts tokens a minute (section 7).

| Tool | Input | Output | Port | Validation |
|---|---|---|---|---|
| `search_entities` | `name`, `type?` | ≤ 5 matches: `entity_id`, `name`, `type`, `year`, `image_url` | `TasteGraph.search` | Non-empty; type in the four we use; rejects text the interpreter flagged as a song title or lyric |
| `find_tags` | `query` | ≤ 5 tags: `tag_id`, `name` | `TasteGraph.tags` | Non-empty |
| `get_insights` | `type`, `signals` (entity and tag IDs), `era?`, `country?`, `popularity_min?`, `take` | Candidates with affinity, image, tags and external IDs | `TasteGraph.insights` | **Adds the profile's `excluded_ids` itself**; maps era to `release_year` or `publication_year` by type and drops it for artists; drops country for artists and books; **drops book signals unless the type is book** (Qloo rejects them); without signals, needs a popularity floor, and artists always need a signal; `take` 1–30 |
| `find_journal_links` | `query`, `kind?` | Existing nodes: `node_id`, `kind`, `title` | journal repository | Scoped to this profile |
| `compare_tastes` | `group_a`, `group_b` (IDs) | Each side's tags and the shared tags | `TasteGraph.compare` | 1–5 IDs per group |
| `submit_candidates` | `[{entity_id, why?}]` | Accepted count | none | The agent's **12 featured picks**, which lead the hero and "Recommended for you". **Accepts only IDs that `get_insights` returned in this run** (rule 1), never an excluded ID. Every other `get_insights` result still joins the pool. Ends the agent's run (`return_direct`) |
| `propose_matches` | `[{entity_id, rung, why}]` | — | none | ≤ 3; IDs must come from this run |
| `propose_links` | proposals (section 5) | — | none | Nodes must exist or be well-formed new nodes |

## 7. Limits

Middleware on `create_agent`: `ToolCallLimitMiddleware` (12 Qloo calls in research, 5 searches
per favourite, 10 per entry), `ModelCallLimitMiddleware` (8), `ToolRetryMiddleware` (temporary
errors only), `ModelFallbackMiddleware` (backup model). An `asyncio` deadline of 25 seconds wraps
the whole research step. Hitting any limit ends research with `limit_hit` or `timeout` and keeps the
candidates already submitted.

Row top-ups in `build_rows` are code, not agent calls. Together with research and the fallback
they stay within `FEED_MAX_QLOO_CALLS` (24) per feed; most are cache hits after the first build.
Research and the fallback record what they spent in `qloo_calls`, and the rows get the rest (until
25 Oct the rows were given 24 minus research's 12-call cap, so calls research didn't use were
wasted and late rows such as `throwback` starved). The song catalogue isn't Qloo and doesn't count.

What we learned from Phase 2 (still true):
- The tools count Qloo calls themselves. When the budget is spent they refuse, telling the agent
  to call `submit_candidates`, so it can still answer. `ToolCallLimitMiddleware` is the hard backstop.
- When research ends early without submitting, keep every recommendation `get_insights` returned;
  they're still Qloo's picks. The fallback then runs only for types that are short.
- Every agent turn resends the history, and free LLM tiers count tokens a minute (Groq's allows
  only 8,000, which is why Gemini became the main model on 24 Oct). Keep tool answers compact JSON
  with short aliases, reasoning effort low, ask for all four `get_insights` calls in one turn,
  submit only the 12 featured picks, and let `submit_candidates` end the run. A live feed for Aanya
  on Gemini: 2 model calls, 4 Qloo calls in research, about 28 seconds in all.
- A provider can't reliably pick up the other's half-finished tool conversation, so the fallback
  mostly helps when the main model fails on its first turn. `ModelFallbackMiddleware` hands a
  failed Gemini call to Groq; Gemini needs a deadline of at least 10 seconds, so its calls get 15.
- Without LLM keys, research is `skipped` and the fallback builds the pool.

## 8. Row strategies

`FeedRow` has two methods: `applies(context)` and `specs(context, pool)`. Each `RowSpec` names the
row's fixed queries (`RowQuery`), which research results it may take (`pool_types`), its order
(`rank`, `featured` or `popularity`), whether to interleave types or take one per type, a fixed
reason, and a minimum size. `build_rows` fills every spec the same way. Rows register in
`RowRegistry` with an order, so earlier rows take items first and later rows can't repeat them.
Items the user already loves (their signals) are never recommended back.

| Order | Key | `applies` | `queries` | `select` |
|---|---|---|---|---|
| 1 | `for_you` | always | none | Top 12 of the pool across all types, at least 2 of each type when available |
| 1b | `cross_culture` (right rail) | an artist, film or show signal | One `get_insights` per *other* type with the newest such signal (an artist → a film, a TV show, a book). Books can't cross types | 1 per type, plus 1 of its own type from the pool: 4 items labelled Watch, Read or Listen |
| 2 | `because_<ref>` | ≥ 1 strong signal | One `get_insights` with the newest strong signal, type = its own type's best cross-domain pair (artist → artist, film → film) | 12 by affinity. Up to 2 such rows, for the two newest strong signals |
| 2b | `journal` | ≥ 1 confirmed journal media link that Qloo knows | `get_insights` per type (the newest item's type, plus one other: an artist → films, a film or show → artists; at most two), with the confirmed journal items as signals | 12, interleaved, by affinity |
| 3 | `music` | always | Top-up artist insights if the pool has < 12 artists | Artists |
| 3b | `songs` | a song catalogue is set up | Not a `FeedRow`: the `add_songs` node (section 3, step 4b) adds it after `build_rows`, from the artists already chosen. No Qloo calls | 2 songs each from up to 6 artists, in turn |
| 4 | `films` | always | Top-up | Films |
| 5 | `tv` | always | Top-up | TV shows |
| 6 | `books` | always | Top-up | Books |
| 6b | `new` | always | Films and TV with `filter.release_year.min` = last year, the top signals; with no signals, popularity ≥ 0.7 and the country | Interleaved films and TV, 12 |
| 7 | `popular_<country>` | country set | Films and TV with `filter.release_country`, popularity ≥ 0.8, the signals | 12 by popularity |
| 9 | `throwback` | birth year set | Films and TV in the era window (`birth_year + 13` to `+ 21`), plus era tags for artists | 12 by popularity |

**Cold start** (chosen in the brief):

| Tier | When | Signals | Filters |
|---|---|---|---|
| A | ≥ 3 verified favourites or strong signals | Those, newest first | `take` per type |
| B | 1–2 favourites | Those, plus quiz picks | Country for films/TV |
| C | Nothing | Quiz picks; if none, popular films for the country, then those films as the signal for artists | **High popularity floor** (0.7) |

Artists must never be asked for with the age signal alone: live tests show that returns generic
bands, because artists have no era filter (`QLOO_NOTES.md`, section 3).

**The taste quiz** (`QuizService`, not a row): a set of about 16 popular, varied items for the
country (cached per country). Pairs: first, two different types; after a tap, the unseen item most
like the pick (`get_insights` with `filter.results.entities` = the unseen set and the pick as the
signal) plus one item of a different type. Each pick is a `quiz_pick` signal (+0.5).

## 9. Fallback and guardrails

**Fallback** runs fixed queries through the same `get_insights` tool, so exclusions still apply.
Results carry `source = qloo_live` or `demo_fixture`, like research results.

**Guardrails** (code only, in this order):
1. Remove anything in `excluded_ids`, matched by ID, and text items by normalised name.
2. Remove items without a `source` or a reason basis (the signal that led to them).
3. Dedupe: an item appears at most once in the feed (hero included), keeping its earliest row.
4. Drop rows below their minimum (4, or 2 for the rail), and if the hero was removed, promote the
   first main-row item with an image. Fewer than 3 main rows is logged as a warning.

Reasons are built in code from each pick's signal (`agent/cards.py`), capped at 120 characters, so
the LLM never writes one. The summary template lives in `application/agent/prompts/templates.py`.

## 10. Research agent system prompt (outline)

1. Role: "You research music, films, TV shows and books that this person will probably love."
2. The brief: signals (names and IDs), recent likes, dismissed types or tags, country, tier.
3. Steps and rules: call `get_insights` once per type, all in the first turn; at most once more
   for a type that came back short; optionally use a tag from `find_tags` to add variety; then
   call `submit_candidates` once with about 8–10 per type, from `get_insights` results only, with
   an optional `why` of up to 8 words. Never search a song title or lyric, and don't search for
   favourites whose IDs are in the brief.
4. It never sees journal text, keys, or anything beyond first name, country and the titles above.

## 11. Agent log style

One entry per decision, in plain English, past tense, no jargon or IDs. Show the step, what was
tried and the outcome, using → and ✓ / ✗:

- "Asked Qloo for films like The Strokes and Lorde → 10 found."
- "Searched singer T. M. Soundararajan → no match. Tried TMS → found (artist) ✓."
- "Hit the 12-call limit; switched to the rule-based picks."
- "Removed 2 items you're not interested in." / "Dropped the TV row (3 items)."
- "Your journal mentioned Interstellar → found (film) ✓."

Entries are `{node, message, level, at}`, where `level` is `info` or `warning`. Never log keys,
journal text, lyrics or raw Qloo responses.

## 12. Privacy boundaries

| Call | May receive |
|---|---|
| Qloo (any endpoint) | Entity IDs, tag IDs, years, country, and names of artists, films, TV shows and books for `/search`. **Never** the user's name, journal text, song titles or lyrics |
| LLM, `research` | First name, country, favourites' and liked items' names, the brief |
| LLM, `interpret` (resolve rung 1) | The user's input for this favourite |
| LLM, `extract` (link) | The text of the one entry being linked (Groq only) |
| LLM, `explain` | Item titles, types and years, signal titles, first name |
| Speech to text | The one recording being transcribed (Groq only); discarded afterwards |
| YouTube (preview only) | Item title, type and year |
| iTunes Search API (songs) | The name of an artist Qloo returned, and the store country. **Never** user text, song titles the user typed, lyrics or journal content |

## 13. Open questions

1. **Settled 24 Oct:** images are on every entity (`properties.image.url`); `external` holds
   Spotify, IMDb, Netflix and Goodreads IDs (QLOO_NOTES, section 6); books steer books only.
2. **Country for music:** films and TV have `filter.release_country`; is there a working location
   signal for artists (`signal.location`)? If not, `popular_<country>` stays films and TV.
3. **Settled by live tests:** both compare paths work; `filter.results.entities` works for scoring;
   `take` defaults to 20; `filter.release_country` needs full country names.
