# Phase 3: Memory Graph

**Dates:** Tue 27 – Wed 28 Oct · **Hours:** about 10 each · **Previous:** [Phase 2](phase-2-core-loop.md) · **Next:** [Phase 4: Bridge and freeze](phase-4-bridge-and-freeze.md)

**Goal:** the signature feature works locally.
- The caregiver writes memory notes, and the agent suggests links to people, places, decades, songs and films.
- The caregiver confirms the links, and they appear in the graph, timeline and list views, with backlinks.
- The next session's prompts use them.
- The favourite resolver ("Type a line you remember") arrives too, because link suggestions reuse its hint ladder.

**Before you start:** Phase 2's exit check has passed. Read `CLAUDE.md`, especially "Memory Graph", "Workflow 2", "Workflow 3" and rule 14.

---

## First: agree the contract (all three, 30 minutes, Tuesday at the start of the evening)

| Route | Request | Response |
|---|---|---|
| `GET /api/v1/profiles/{id}/memory/nodes?kind=&q=` | query string | `MemoryNode[]`, for the list view and the `[[` picker |
| `POST /api/v1/profiles/{id}/memory/nodes` | `{ kind, title, body?, year?, qloo_id? }` | `MemoryNode` |
| `GET /api/v1/profiles/{id}/memory/nodes/{node_id}` | nothing | `{ node, links, backlinks, suggestions }` |
| `PATCH /api/v1/profiles/{id}/memory/nodes/{node_id}` | `{ title?, body?, year?, use_in_prompts? }` | `MemoryNode` |
| `DELETE /api/v1/profiles/{id}/memory/nodes/{node_id}` | nothing | `204`. Its links go too |
| `POST /api/v1/profiles/{id}/memory/nodes/{node_id}/suggest-links` | nothing | `{ agent_run_id }`. Suggestions are saved as links with status `suggested` |
| `POST /api/v1/profiles/{id}/memory/links` | `{ from_id, to_id, kind }` | `MemoryLink`. A manual link, already confirmed |
| `PATCH /api/v1/profiles/{id}/memory/links/{link_id}` | `{ status: confirmed \| rejected }` | `MemoryLink` |
| `GET /api/v1/profiles/{id}/memory/graph` | nothing | `{ nodes, links }`. Confirmed links only, at most `MEMORY_GRAPH_MAX_NODES` nodes |
| `GET /api/v1/profiles/{id}/memory/timeline` | nothing | `[{ decade, nodes }]` |
| `POST /api/v1/profiles/{id}/memory/nodes/{node_id}/promote` | nothing | `Favourite` |
| `POST /api/v1/profiles/{id}/favourites/resolve` | `{ text }` | `{ agent_run_id }`. The run's `result` holds up to 3 proposals |

**`MemoryNode`** has these fields:
- `id`
- `kind`: `person`, `place`, `decade`, `memory`, `song`, `artist`, `movie`, `tv_show`, `book` or `session`
- `title`
- `body`
- `year`
- `decade`
- `qloo_id`
- `use_in_prompts`
- `pending`
- `created_by`: `caregiver`, `agent` or `system`

**`MemoryLink`** has these fields:
- `id`
- `from_id`
- `to_id`
- `kind`: `mentions`, `because_of`, `reacted`, `from_movie`, `in_decade`, `lived_in` or `related`
- `source`: `caregiver`, `agent`, `qloo` or `session`
- `status`: `suggested`, `confirmed` or `rejected`
- `reason`

**Pending nodes.** When the agent suggests a link to someone or something new (for example a person called Ruth), it creates the node with `pending: true`.
- A pending node is hidden from the views and the `[[` picker until one of its links is confirmed.
- If the suggestion is rejected, the node stays hidden and the rejected link is kept, so the agent never suggests it again.

---

## Agent: resolver, link suggestions, personal prompts (≈ 10 h)

### Agent 1. The `resolve_favourite` workflow
- It climbs the hint ladder from `CLAUDE.md`, logging each rung.
- At most `RESOLVE_MAX_SEARCHES` (5) searches.
- It checks type, year and name before accepting a match.
- It returns up to 3 proposals.

This also improves coverage for older and Indian titles.

### Agent 2. The `find_memory_nodes` tool
A thin wrapper over the memory repository port. It includes pending nodes, so rejected suggestions can be recognised.

### Agent 3. The `link_memory` workflow
1. **Extract mentions** with structured output: people, places, years or decades, songs, artists, films, TV shows and books.
2. **Resolve the songs, artists, films, TV shows and books** with the hint ladder. Stay within `LINK_MAX_SEARCHES` (10) in total.
3. **Match people and places** to existing nodes with `find_memory_nodes`. Create pending nodes for new ones.
4. **Skip anything already rejected** for this note.
5. **Save the suggestions** with `propose_links`, each with a short reason.

### Agent 4. Personal prompts in `compose`
- For each item, load confirmed links from the item (and from its artist or film) to person, place, memory and decade nodes with "Use in prompts" on.
- Send the LLM only those nodes' **titles**.
- Prompts stay open and gentle. For example: "This came out the year of the Saturday dances. What was the music like there?"
- The template fallback can use a place or a decade.

### Agent 5. Record why each item was picked
`select_items` stores `because_of_ref` on each session item: the favourite or signal that led to it. The backend's auto-links use it.

### Agent 6. Demo memories
For each sample profile:
- 4–6 hand-written notes covering people, places and occasions;
- their links;
- everything marked `"demo": true`.

### Agent 7. Tests
- **Note text never reaches the Qloo adapter** (use a spy adapter).
- The ladder stops at 5 searches, and a link run stops at 10.
- Nodes with "Use in prompts" off never reach `compose`.
- Suggested links don't affect prompts or signals.
- A rejected suggestion isn't proposed again.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("The agent", "Memory Graph", rule 14) and docs/AGENT.md. Build
workflows/resolve_favourite.py (the hint ladder from CLAUDE.md, max
RESOLVE_MAX_SEARCHES, accept a match only after checking type, year and name, up to
3 proposals, every rung logged) and workflows/link_memory.py (structured extraction
of people, places, years, songs, artists, films, TV shows and books; resolve media
mentions with the hint ladder within LINK_MAX_SEARCHES in total; match people and
places with a new find_memory_nodes tool, creating pending nodes for new ones; skip
previously rejected links; save suggestions via propose_links with a reason). In
compose, personalise prompts using only the titles of confirmed, "Use in prompts"
nodes linked to each item; keep prompts open and gentle, with a template fallback.
Store because_of_ref on session items in select_items. Tests: note text never reaches
the Qloo adapter (spy), search limits, Use-in-prompts off never reaches compose,
suggested links have no effect, rejected suggestions are not re-proposed.
Run ruff and pytest.
```

**Check:**
- A note like "Saturday dances in Chicago with her sister Ruth, around 1966" gets sensible suggestions: Ruth (person), Chicago (place), the 1960s (decade).
- "Type a line you remember" finds the right singer for a well-known song.

---

## Backend: memory storage, auto-links, routes (≈ 10 h)

### Backend 1. Migration and repositories
- `memory_nodes` and `memory_links`, with RLS on.
- A unique key on `(from_id, to_id, kind)`.
- Add `because_of_ref` to `session_items`.
- In-memory and Postgres repositories.

### Backend 2. `MemoryService`
- Create, edit and delete nodes and notes.
- Manual links, saved as confirmed.
- Confirming a suggestion clears `pending` on its target node.
- Backlinks.
- **The graph:**
  - confirmed links and visible nodes only;
  - capped by keeping the most connected nodes, then the most recent.
- **The timeline:** nodes grouped by decade.
- Deleting a profile deletes its memory.

### Backend 3. Automatic links
These live in the services, never in routes:
- **A favourite is added:** create its node, plus an `in_decade` link.
- **Places lived:** create place nodes, plus `lived_in` links.
- **A positive reaction** (sang along or smiled) **or a ♥:**
  - create the item's node;
  - add a `reacted` link from the session node;
  - add a `because_of` link to the favourite in `because_of_ref`.

### Backend 4. Routes
- The whole contract, with ownership checks.
- `suggest-links` and `favourites/resolve` start agent runs (kinds `link` and `resolve`), polled like planning.

### Backend 5. Promote to favourite
A song, artist, film, TV show or book node becomes a favourite. It's verified when it has a Qloo ID.

### Backend 6. Demo seed
- Add the agent's demo memories.
- Resolve their song, artist and film nodes by name through `TasteService.search`, as with favourites.

### Backend 7. Tests
- Cross-user access is denied.
- The graph respects its cap.
- Pending nodes stay hidden.
- A rejected link stays rejected.
- The automatic links are created.
- Promote works.
- Deleting a profile deletes its memory.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Memory Graph", rule 14) and docs/API_CONTRACT.md (Phase 3). Add
memory_nodes and memory_links (RLS on, unique from/to/kind) and because_of_ref on
session_items, with an Alembic migration and in-memory + Postgres repositories.
Implement MemoryService: node and note CRUD, manual links (confirmed), confirm or
reject suggestions (confirming clears pending on the target), backlinks, a capped
graph (confirmed links and visible nodes only; most connected, then most recent), a
decade timeline, cascade deletes. Add automatic links in the services: favourite ->
node + in_decade; places lived -> place nodes + lived_in; positive reaction or ♥ ->
item node + reacted (from the session node) + because_of (to because_of_ref).
Implement all Phase 3 routes with ownership checks; suggest-links and
favourites/resolve start agent runs. Seed the agent's demo memories, resolving media nodes
by name. Tests: cross-user 404, graph cap, pending hidden, rejected stays rejected,
auto-links, promote, cascade delete. Run ruff and pytest.
```

**Check:** every Phase 3 route works in `/docs` against the seeded demo memories.

---

## Frontend: memory screens and the lyric box (≈ 10 h)

### Frontend 1. Pick the graph library (first hour)
- Try react-force-graph and Cytoscape.js against the graph response.
- Pick one, and tell the team (`CLAUDE.md`, rule 17).

### Frontend 2. Memory note editor
- A title, the text, and a year or decade.
- The hint "Please don't add medical details."
- Typing `[[` opens a picker. It searches nodes and can create a new person, place or other node inline.

### Frontend 3. Suggested links panel
- After saving a note, the agent's run is polled, and its log is shown.
- Suggestions appear as chips, such as "Ruth · person", each with ✓ and ✗.
- A "Confirm all" option.

### Frontend 4. Node page
- The node's title, kind, text and links.
- **Backlinks.**
- The "Use in prompts" switch.
- "Add as favourite", for song, artist, film, TV and book nodes.
- Delete.

### Frontend 5. Views (`/profiles/:id/memories`)
- **List:** the default on phones, with filtering by kind and search.
- **Timeline:** grouped by decade.
- **Graph:**
  - capped;
  - coloured by kind and grouped by decade;
  - tapping a node opens its page;
  - an empty state that suggests adding a first memory.

### Frontend 6. "Type a line you remember" (favourites editor)
1. It sends the text to `favourites/resolve` and polls the run.
2. It shows up to 3 proposals, with type and year.
3. The caregiver taps one to confirm it, or adds a hint (singer, film or year) to run it again.
4. The box clears afterwards. The lyric is never shown again or saved.

### Frontend 7. Caregiver conversation (Wednesday)
- Show the app, and note the feedback.
- Ask for a quote you're allowed to use.

**Prompt for Claude Code:**
```
Read CLAUDE.md ("Memory Graph", "Frontend conventions") and docs/API_CONTRACT.md
(Phase 3). Build features/memory-graph: a note editor (title, text, year or decade,
the hint "Please don't add medical details", a [[ picker that searches nodes and can
create one inline); a suggested-links panel (polls the link run, shows its log,
chips with confirm/reject and "Confirm all"); a node page (links, backlinks,
"Use in prompts" switch, "Add as favourite" for media nodes, delete); and three
views at /profiles/:id/memories: list (default on phones, filter by kind, search),
decade timeline, and a capped graph with <chosen library>, coloured by kind,
grouped by decade, tap to open. In the favourites editor add "Type a line you
remember": post to /favourites/resolve, poll the run, show up to 3 proposals, tap
to confirm or add a hint; clear the box afterwards and never show or store the
lyric. Loading, empty and error states, phone layout, keyboard access.
Run lint and build.
```

**Check:** add a note, confirm its links, and find the note in all three views on a phone and a laptop.

---

## Exit check (Wednesday night)

Locally (backend also run once from its Docker image):
1. Open Margaret's memories. The seeded notes show in the list, timeline and graph.
2. Add the note "Saturday dances in Chicago with her sister Ruth, around 1966", and confirm the suggested links.
3. Ruth's page shows the note as a backlink.
4. Plan a session. A prompt uses the memory.
5. Turn off "Use in prompts" for Ruth, and plan again. She isn't mentioned.

## If you're behind

- **Cut first:** the graph view. Keep the list, the timeline and backlinks.
- **Then cut:** "Type a line you remember".
- **If it still isn't done by Wednesday night:** cut Bridge entirely and use Thursday to finish this phase.
- **Never cut:** caregiver confirmation of links, the privacy rules, the "Use in prompts" switch.
