---
version: 1
slug: "frontend-src-pages-homepage-tsx"
primary_target: "frontend/src/pages/HomePage.tsx"
related_targets: []
---

# Surface brief: Home feed

Scope: the signed-in home screen (`/p/:profileId`) and its shell (sidebar, top bar, right rail, detail sheet). Mode: Operate. Build path: code-led (working screen).

Audience and job: anyone who wants the next thing to play, watch or read across music, films, TV and books, and to see why it was picked. Task: scan rows, open a pick where it lives, like / save / dismiss, refresh and see the feed change.

Constraints: layout pinned by the user's mockup `image.png` (left sidebar with taste chips, top search, hero banner, category tiles, rows with "See all", right rail with vibe chips, quick actions, cross-culture picks); light look pinned to the CLAUDE.md "Design system" tokens (Chillax + Switzer, ink #1A1A1A, amber #E8A838, type colours music/film/tv/book). Phone first; WCAG 2.2 AA. Voice: bold and playful.

Memorable moment: the taste thread drawn from what you love to what it led to, across types.

## Direction contract

THESIS: A home screen that shows the wiring of your taste: every pick hangs on a visible thread back to the thing you love that caused it, crossing music, screen and page. It refuses the category default of anonymous poster walls where nothing says why.

OWN-WORLD: White ground, ink type, one amber accent for action and selection; four type colours (amber music, coral film, blue TV, green book) used only as meaning: chips, thread strands, fallback tiles. Chillax for headlines and row titles, Switzer for everything else. Soft offset shadows, 10–16 px radii, hairline borders, glass top bar.

STORY: The visitor sees their top pick and why, scans rows that each name their reason, follows the thread from a favourite to a film to a book, taps one to open it on its platform, likes or dismisses, refreshes, and reads what changed.

FIRST VIEWPORT: Desktop: 248 px white sidebar (logo, nav, taste chips) left; sticky glass top bar with search and "Hey, Aanya"; main column with a 16 px-radius hero banner (top pick image right, ink-to-transparent gradient left, Chillax headline with one amber word, reason, primary "Open on Spotify" button, secondary "Why this?"), then three category tiles, then the first row; 320 px right rail with vibe chips, quick actions and the cross-culture thread. Phone: hero full width, rail sections become rows, bottom tabs.

FORM: Pinned by the user's brief (mockup layout plus light token set); signature move: the taste thread (colour strands linking because-of source to picks in the rail and the detail sheet). seed: none (pinned by user brief)

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
