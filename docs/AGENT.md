# The MeloMind agent: design

Owner: the agent owner. Reviewer: the backend owner. This is the design for `backend/app/application/agent/` and
`application/modes/`. It adds detail to `CLAUDE.md` ("The agent", "Cold start", "Person mode",
"Memory Graph") and never overrides it. Qloo specifics are in `docs/QLOO_NOTES.md`.

---

## 1. Shape

- **One agent, three workflows**, all sharing one set of tools: `plan_session`,
  `resolve_favourite` and `link_memory`.
- **Hybrid.** Each workflow is a fixed LangGraph `StateGraph` where code sets the order. Only the
  `research` step of `plan_session` is a tool-calling agent (LangChain `create_agent`) that
  chooses its own Qloo calls. It compiles to a graph and runs as one node.
- **Ports only.** Nodes and tools receive `TasteGraph`, `MediaResolver`, `LanguageModel` and the
  repositories from the workflow builder. They never import an adapter.
- **Every run is an `agent_run`** (kind `plan`, `resolve` or `link`) with a status (`running`,
  `done`, `failed`, `needs_hint`) and a plain-English log. The frontend polls
  `/agent-runs/{id}`.
- **A result is always produced.** When the agent fails or hits a limit, code takes over.

## 2. State

Shared by all workflows: `run_id`, `profile_id`, `log` (list of entries), `limits` (counters
for tool calls, model calls and the deadline), `errors`.

**`PlanState`**

| Field | Written by | Holds |
|---|---|---|
| `mode`, `brief` | start, `research` | The mode's name and its research brief |
| `context` | `load_context` | Profile (first name, birth year, country, places, languages), verified favourites with Qloo IDs, text favourites, feedback totals, `blocked_ids` (rejected and upset), `learned_weights`, prompt-allowed titles of confirmed memory links per item |
| `candidates` | `research`, `fallback` | `{entity_id, name, type, year, popularity, affinity, source, signal}` |
| `research_outcome` | `research` | `ok`, `too_few`, `limit_hit`, `timeout` or `error` |
| `fallback_attempts` | `fallback` | 0–2 |
| `ranked`, `selected`, `spares` | `select_items` | Ordered candidates |
| `media` | `resolve_media` | Per item: video ID, duration, or "No playable version found" |
| `items` | `guardrails`, `compose` | Final session items with `source`, `reason`, `prompts`, `duration_s` |

**`ResolveState`**: `input_text` (never stored after the run), `kind_hint`, `interpretation`
(`song_title`, `singer`, `composer`, `film`, `year`), `steps_tried`, `proposals` (≤ 3),
`question` (when the run ends with `needs_hint`).

**`LinkState`**: `note_id`, `note_text` (held in memory for this run only, never logged),
`mentions`, `resolved` (mention → Qloo entity), `node_matches` (mention → existing node), `proposals`.

## 3. Workflow 1: `plan_session`

| # | Step | Reads → writes | Logs (example) | On failure |
|---|---|---|---|---|
| 1 | `load_context` (code) | `profile_id` → `context` | "Loaded Margaret: born 1948, Chicago, 4 favourites, 2 blocked items." | Profile missing: run `failed` (404 at the API) |
| 2 | `research` (**agent**) | `brief`, `context` → `candidates`, `research_outcome` | Each tool call (section 6), then "Submitted 14 candidates." | Any error, limit or timeout: keep what was found, set the outcome, go on |
| 3 | `fallback` (code) | Runs only if the outcome isn't `ok` or there are fewer than the mode's minimum. Mode's `fallback_queries`, then `relax` up to `AGENT_MAX_RETRIES` (2) | "Agent found 3 items; running the rule-based plan. Widened the era to 1956–1974." | Still too few: continue with what exists; the log says so |
| 4 | `select_items` (code) | `candidates`, `learned_weights` → `ranked`, `selected`, `spares` | "Picked 4 artists, 2 films, 1 TV show, 1 book, plus 4 spares." | — |
| 5 | `resolve_media` (code) | `selected` → `media` | "No playable version of Shindig!; swapped in Bewitched." | Unplayable: use a spare of the same type. Never an unrelated video |
| 6 | `guardrails` (**code only**) | `selected`, `media`, `blocked_ids` → `items` | "Removed 1 blocked item. Session is 20 min 40 s." | See section 9 |
| 7 | `compose` (LLM + template) | `items`, profile basics, prompt-allowed linked titles → `reason`, `prompts` | "Wrote reasons and prompts." or "LLM timed out; used templates." | Invalid output or 15-second timeout: templates |

Media rules: an artist item resolves to an embeddable YouTube video found by searching the
artist's name and era; the video's own title is shown. A song favourite searches
`"<song_title> <singer>"`. Films and TV resolve to a clip or theme. Books: see section 12.

## 4. Workflow 2: `resolve_favourite` (the hint ladder)

Input: whatever the caregiver typed, plus an optional kind. Stop at the first accepted match.
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
| 8 | Ask the caregiver for a hint (singer, film or year). Run ends `needs_hint` | none |
| 9 | Keep as text: playable and usable in prompts, not a Qloo signal | none |

- **Never search Qloo for a song title or lyric.** A lyric is used in rung 1 only, then dropped.
  The log says "Interpreted a lyric hint", never the lyric.
- **Acceptance (code):** the result's type matches the rung's expected type; the name matches
  after normalising case, punctuation and initials; and, when both years are known, the year is
  within 5 years for films and books. An artist with no year passes on name and type.
- **Output:** up to 3 proposals `{entity_id, name, type, year, rung, why}`. The caregiver
  confirms one, and only then is it saved as a verified favourite.

## 5. Workflow 3: `link_memory`

1. **Extract** (LLM, structured output) from the note text. Schema:
   `mentions: [{ kind, text, year?, relation?, confidence }]`, where `kind` is one of `person`,
   `place`, `year`, `decade`, `song`, `artist`, `movie`, `tv_show`, `book`; `relation` is for people
   ("sister"); `confidence` is 0–1. Mentions under 0.5 confidence are dropped.
2. **Resolve** songs, artists, films, TV shows and books with the hint ladder (shared budget of
   `LINK_MAX_SEARCHES`, 10, per note).
3. **Match** people and places to existing nodes with `find_memory_nodes`, or propose a new node.
   Years and decades map to `decade` nodes.
4. **Propose links**: `{ target: node_id | new_node {kind, title, year?, qloo_id?}, link_kind,
   evidence }` with `source = agent`, `status = suggested`. Code drops any proposal whose
   `(from, to, kind)` was rejected before. The caregiver confirms each one with ✓ or ✗.

## 6. Tools (`agent/tools/`)

Each is a thin wrapper over a port. Each validates its inputs and logs its call and result count.

| Tool | Input | Output | Port | Validation |
|---|---|---|---|---|
| `search_entities` | `name`, `type?` | ≤ 5 matches: `entity_id`, `name`, `type`, `year` | `TasteGraph.search` | Non-empty; type in the four we use; rejects text the interpreter flagged as a song title or lyric |
| `find_tags` | `query` | ≤ 5 tags: `tag_id`, `name` | `TasteGraph.tags` | Non-empty |
| `get_insights` | `type`, `signals` (entity and tag IDs), `era?`, `country?`, `popularity_min?`, `take` | Candidates with affinity | `TasteGraph.insights` | **Adds the profile's `blocked_ids` itself**; maps era to `release_year` or `publication_year` by type and drops it for artists; drops country for artists and books; `take` 1–20 |
| `find_memory_nodes` | `query`, `kind?` | Existing nodes: `node_id`, `kind`, `title` | memory repository | Scoped to this profile |
| `compare_tastes` (Phase 4) | `group_a`, `group_b` (IDs) | Shared and bridging entities | `TasteGraph.compare` | 1–5 IDs per group |
| `submit_candidates` | `[{entity_id, why}]` | Accepted count | none | **Rejects any ID not returned by a tool in this run** (rule 9) and any blocked ID |
| `propose_matches` | `[{entity_id, rung, why}]` | — | none | ≤ 3; IDs must come from this run |
| `propose_links` | proposals (section 5) | — | none | Nodes must exist or be well-formed new nodes |

## 7. Limits

Middleware on `create_agent`: `ToolCallLimitMiddleware` (12 Qloo calls per plan, 5 searches per
favourite, 10 per note), `ModelCallLimitMiddleware` (8), `ToolRetryMiddleware` (temporary errors
only), `ModelFallbackMiddleware` (backup model). An `asyncio` deadline of 25 seconds wraps the
whole research step. Hitting any limit ends research with `limit_hit` or `timeout` and keeps the
candidates already submitted.

## 8. Session modes

`SessionMode` has four methods: `research_brief(state)`, `fallback_queries(state)`,
`relax(queries, attempt)` and `select(ranked, state)`. Modes register in `ModeRegistry` by name;
the plan endpoint takes `mode` and nothing else changes.

**Cold-start tiers** (chosen by `research_brief` from the context):

| Tier | When | Signals | Filters |
|---|---|---|---|
| A | ≥ 3 verified favourites | The favourites, plus learned items with weight ≥ 0.6 | Era window, country for films/TV, `take` per type |
| B | 1–2 favourites or a hint | Those, plus the hint ladder's result (singer, film or tag) | Era, country, age signal |
| C | Nothing specific | Films, TV, books: `signal.demographics.age=55_and_older` (plus a region tag if known). **Artists:** the top era films just found, plus an era or region music tag | Era, country, **high popularity floor** (0.7): the big hits of their youth |

Tier C artists must never be asked for with the age signal alone: live tests show that returns
today's biggest bands, because artists have no era filter (`QLOO_NOTES.md`, section 3).

**`standard`**: goal "a 20-minute session they're likely to love". Mix 4 artists, 2 films,
1 TV show, 1 book, plus 4 spares. Minimum 8 candidates. Fallback: one `get_insights` per type with
the tier's signals. Relax: widen the era by 5 years per attempt, then lower the popularity floor
by 0.2.

**`warmup`**: about 12 varied, well-known items across types and decades of their era, popularity
floor 0.7, all playable. `compose` skips the LLM: Person mode never shows prompts. The caregiver
approves the set like any session.

**`bridge`** (Phase 4): elder's signals vs a visitor's 3 favourites through `compare_tastes`.
Compare returns each side's tags and the shared tags, not items; the shared tags then become
`signal.interests.tags` in an ordinary `get_insights` call.

## 9. Fallback and guardrails

**Fallback** runs the mode's fixed queries through the same `get_insights` tool, so exclusions
still apply. Results carry `source = qloo_live` or `demo_fixture`, like research results.

**Guardrails** (code only, in this order):
1. Remove anything in `blocked_ids` (rejected or upset), matched by ID, and text items by
   normalised name.
2. Remove items without a `source` or a reason basis (the signal that led to them).
3. Remove items with no playable video; refill from spares of the same type, then any spare.
4. Fit the target: `SESSION_TARGET_MINUTES` ± 10 % (18–22 minutes). Add spares while short; drop
   the lowest-ranked item while long.
5. After `compose`, check text in code: a prompt starting "Do you remember" or containing a
   medical claim ("treats", "improves memory", "reduces agitation"…) is replaced by a template.

## 10. Research agent system prompt (outline)

1. Role: "You research songs, films, TV and books for a caregiver-led music and memory session."
2. The brief: goal, mix, era window, country, popularity floor, caregiver instructions, tier.
3. Allowed signals: the verified favourites' IDs and names, learned items, region tags.
4. Rules: use only tool results; never search a song title or lyric; one `get_insights` per type
   at most twice; stop when you have about twice the mix; then call `submit_candidates` with a
   one-line `why` for each.
5. It never sees memory note text, keys, or anything beyond first name, birth year, places and
   favourites.

## 11. Agent log style

One entry per decision, in plain English, past tense, no jargon or IDs. Show the step, what was
tried and the outcome, using → and ✓ / ✗:

- "Searched singer T. M. Soundararajan → no match. Tried TMS → found (artist) ✓."
- "Asked Qloo for films like The Sound of Music, 1961–1969 → 12 found."
- "Hit the 12-call limit; switched to the rule-based plan."
- "Removed Gone with the Wind: outside the era." / "Removed 1 item the caregiver rejected."

Entries are `{at, step, message, level}`. Never log keys, memory note text, lyrics or raw Qloo
responses.

## 12. Privacy boundaries

| Call | May receive |
|---|---|
| Qloo (any endpoint) | Entity IDs, tag IDs, the age bracket, years, country, and names of artists, films, TV shows and books for `/search`. **Never** the person's or family's names, note text, song titles or lyrics |
| LLM, `research` | First name, birth year, places, favourites' names, the brief |
| LLM, `interpret` (resolve rung 1) | The caregiver's input for this favourite |
| LLM, `extract` (link) | The text of the one note being linked |
| LLM, `compose` | Item titles, types and years, first name, birth year, places, and titles of confirmed linked nodes with "Use in prompts" on |
| YouTube | Item title, artist or song title, decade |

## 13. Open questions (for the backend owner and the team)

1. **Books in sessions:** books rarely have a playable video. Options: a fixed conversation slot
   (no video, counts as about 3 minutes), or a clip of the film adaptation. Person mode skips them
   either way, since the shelf needs a playable video.
2. **Artists to songs:** we play the YouTube result for "<artist> <decade>". Is showing that video's
   title on the card acceptable, given titles can be messy?
3. **Settled by live tests:** both compare paths work; `filter.results.entities` works for the
   warm-up; `take` defaults to 20, not 5; `filter.release_country` needs full country names.
   `CLAUDE.md` should be corrected on `take`.
