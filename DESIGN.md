---
name: MeloMind
description: Your personal culture companion — one home screen for music, films, TV and books.
colors:
  ink: "#1A1A1A"
  body: "#444444"
  muted: "#6B6B6B"
  surface: "#FFFFFF"
  surface-2: "#F5F5F5"
  surface-3: "#ECECEC"
  line: "#E0E0E0"
  hairline: "#0000000F"
  amber: "#E8A838"
  amber-hover: "#D4952E"
  amber-ink: "#8A5A0C"
  brand-yellow: "#FFC700"
  music: "#E8A838"
  film: "#E0594A"
  tv: "#4A7BE0"
  book: "#3E9C6B"
  music-ink: "#8A5A0C"
  film-ink: "#B0372A"
  tv-ink: "#2F5BB8"
  book-ink: "#2A7350"
  danger: "#C2412F"
typography:
  display:
    fontFamily: "Chillax, Switzer, ui-sans-serif, sans-serif"
    fontSize: "46px"
    fontWeight: 600
    lineHeight: 1.05
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Chillax, Switzer, ui-sans-serif, sans-serif"
    fontSize: "34px"
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Chillax, Switzer, ui-sans-serif, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.03em"
  body:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Switzer, ui-sans-serif, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    letterSpacing: "0.05em"
rounded:
  pill: "999px"
  sm: "8px"
  card: "10px"
  panel: "12px"
  hero: "16px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "14px"
  lg: "24px"
  xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    height: "44px"
    padding: "0 20px"
  button-primary-hover:
    backgroundColor: "{colors.amber-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    height: "44px"
    padding: "0 20px"
  button-dark:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.sm}"
    height: "44px"
  chip-toggle-selected:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "40px"
  chip-tag:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body}"
    rounded: "{rounded.pill}"
    height: "32px"
  search-field:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    height: "44px"
  feed-card-image:
    rounded: "{rounded.card}"
  rail-panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "16px"
  hero-banner:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
    rounded: "{rounded.hero}"
---

# Design System: MeloMind

## Overview

**Creative North Star: "The Taste Thread"**

MeloMind is a bright, airy home screen where everything connects. Every pick hangs on a visible strand back to the thing you love that caused it, and the strand takes the colour of where it leads: amber for music, coral for film, blue for TV, green for books. The interface itself stays quiet and white so the covers and the threads do the talking.

The page reads like the best streaming home screens (sidebar, search, hero, rows) with one move none of them have: the wiring of your taste is drawn, not hidden. The thread appears in three places at three scales: the cross-culture rail (a vertical thread through four types), the "Why you're seeing this" strip in the detail sheet, and a short strand under every card naming its source.

Density is generous but not sparse: rows of 2.3, 4.5 or 6.5 cards by width, 14 px gutters, and real images everywhere. The voice is bold and playful in headlines ("Listen to Arctic Monkeys") and plain everywhere else.

**Key Characteristics:**
- White ground, ink type, one amber accent for action and selection.
- Four type colours used only as meaning: chips, thread strands, fallback tiles.
- Chillax for anything that's a heading; Switzer for everything you read or tap.
- Real Qloo images on every card; a designed gradient tile when there's none.
- Motion is quiet: a 2 px lift on hover, a drawer that glides, a thread that grows once.

## Colors

A white, ink and amber system, with four type colours that only ever mean "what kind of thing this is".

### Primary
- **Spotlight Amber** (`amber`): primary buttons, the selected mood chip, the focus ring, the one highlighted word in a headline, the "Refresh for new picks" state. Its rarity is its power.
- **Amber Ink** (`amber-ink`): amber-family text on white, where amber itself would fail contrast (links like "See all", active icons).

### Secondary (the type colours)
- **Music Amber** (`music`), **Film Coral** (`film`), **TV Blue** (`tv`), **Book Green** (`book`): dots, thread strands, avatar fills and fallback gradients.
- Their **ink partners** (`music-ink`, `film-ink`, `tv-ink`, `book-ink`) carry type labels as text on white at 4.5:1 or better.

### Neutral
- **Ink** (`ink`): headings, primary text, dark buttons and the hero's ground.
- **Body Grey** (`body`): running text.
- **Muted Grey** (`muted`): secondary text, card sources, hints.
- **Paper White** (`surface`): the page and every panel.
- **Soft Grey** (`surface-2`, `surface-3`): the search field, hover rows, skeletons and the "why" panel.
- **Line** (`line`) and **Hairline** (`hairline`): borders; hairline for panels that should barely separate.

### Named Rules
**The Meaning-Only Rule.** A type colour appears only where it says "this is music / film / TV / a book". Never as decoration, never as a section background.

**The One Amber Rule.** Amber marks the single next action on a surface (one primary button, the selected chip, the highlighted word). Two amber buttons side by side means one of them is wrong.

## Typography

**Display Font:** Chillax 600 (with Switzer, sans-serif)
**Body Font:** Switzer 400–700 (with system sans-serif)

**Character:** Chillax is rounded, compact and a little cheeky: it gives headlines the bold, playful voice. Switzer is a calm, neutral workhorse that keeps reasons, labels and controls easy to scan.

### Hierarchy
- **Display** (600, 34–46 px, 1.05): the hero's headline, with its verb in amber ("Listen to", "Watch", "Read").
- **Headline** (600, 34–52 px, 1.1): page titles (Who's exploring?, Discover, Saved).
- **Title** (600, 18–22 px, 1.2): row titles and panel titles.
- **Body** (400, 15–16 px, 1.5): reasons, descriptions, status lines; keep to about 65ch.
- **Label** (600, 12 px, +0.05em, uppercase): type chips ("● FILM"), the thread's verbs (LISTEN, WATCH, READ).

### Named Rules
**The No-Eyebrow Rule.** Headings speak for themselves: no kicker or label above a heading. Type and year go below the title.

**The Chillax-Is-For-Headings Rule.** Chillax never sets a paragraph, a button label or a card title in a row; card titles use Switzer 600 so long titles stay readable.

## Layout

Desktop is three columns: a 248 px white sidebar (logo, nav, taste chips), the main column, and a 320 px right rail (taste thread, quick actions, vibe). The top bar is sticky and glass. Below 1280 px the rail moves under the rows and the thread moves up under the category tiles; below 1024 px the sidebar becomes bottom tabs (Home, Discover, Saved, Profiles).

Rows scroll sideways with snap, showing 2.3 cards on phones, 4.5 on tablets and 6.5 on desktop, so the next card always peeks. Sections are separated by 28–36 px; groups inside them by 10–14 px. Phone gutters are 16 px; desktop gutters 24 px.

### Named Rules
**The Peek Rule.** A row never ends on a card edge: the partial card is the affordance that says "scroll me".

## Elevation & Depth

Flat at rest, lifted by interaction. Panels separate with a hairline and a soft ambient shadow; cards lift on hover; sheets and menus float.

### Shadow Vocabulary
- **Soft** (`0 2px 12px #0000000F`): rail panels, buttons on hover, small controls on images.
- **Lift** (`0 10px 28px -8px #00000024`): hovered cards, open menus, toasts.
- **Sheet** (`0 -12px 40px -12px #00000040`): the detail sheet and drawer.

### Named Rules
**The Lift-On-Intent Rule.** A card has no shadow until the pointer is on it; then it rises 2 px and scales to 1.03. Never on touch devices.

## Shapes

Rounded but not soft: 8 px buttons, 10 px cards and images, 12 px panels and tiles, 16 px for the hero and the sheet. Pills (999 px) for chips, badges and the avatar. Artist images in compact lists are circles; everything else stays rectangular. Hairline borders, never thick ones, and never a coloured stripe on one side.

## Components

### Buttons
- **Shape:** gently rounded (8 px), at least 44 px tall.
- **Primary:** amber fill, ink label, 0 20 px padding; on hover a darker amber, a 1 px lift and a warm glow.
- **Secondary:** white with a light grey border; on hover the border darkens and it lifts 1 px.
- **On-image:** frosted white glass with a light border, for the hero only.
- **Dark:** ink fill, white label, for the YouTube preview.
- **Focus:** a 3 px amber ring, offset 2 px.

### Chips
- **Type chip:** uppercase label in the type's ink colour after a 6 px dot in the type colour.
- **Tag chip:** white pill, hairline border, body text.
- **Toggle chip (moods):** white pill with a line border; selected fills amber with ink text.
- **Source badge:** "Live Qloo" in green on a green tint, or "Demo data" in grey.

### Cards
- **Image:** fixed aspect (square for artist rows, 2:3 posters, 3:4 in mixed rows), 10 px radius, lazy-loaded with a blur-up; the fallback is the type's gradient tile with its icon and title.
- **Actions:** a heart that's always reachable; save and "not interested" appear on hover or focus.
- **Text:** type chip and year, the title in Switzer 600 (two lines), then the taste strand and its source.

### Inputs / Fields
- **Search:** a soft grey, 10 px rounded field with a search icon; on focus it turns white with an amber border. Results drop into a floating panel with image thumbnails and "Add to my taste".

### Navigation
- **Sidebar:** 44 px rows; the active row is an amber-tinted pill with ink text and an amber-ink icon. Not-yet-built sections show a quiet "Soon" pill rather than a dead link.
- **Bottom tabs (phones):** four tabs, active icon in amber-ink.

### Taste Thread (signature)
- **Rail:** a vertical thread starting at an ink node ("Because you like Glass Animals"), then one node per pick in its type colour, each strand a gradient from the previous colour to the next; picks carry a 48 px thumbnail and a verb label (Listen / Watch / Read). It grows in once, staggered by 90 ms.
- **Card strand:** a 16 × 3 px gradient from ink to the card's type colour, followed by the source's name.
- **Detail strip:** source pill, a gradient strand, and the item pill tinted in its type colour, followed by the reason and the Qloo match.

## Do's and Don'ts

### Do:
- **Do** draw the thread wherever a pick has a source: rail, card strand, detail strip.
- **Do** keep amber to the single next action on a surface.
- **Do** use Qloo's image or the designed fallback tile on every card; rows never show an empty box.
- **Do** label search links honestly ("Search on Netflix") and direct ones as "Open on".
- **Do** respect `prefers-reduced-motion`: fades replace movement.

### Don't:
- **Don't** put a kicker or eyebrow label above a heading.
- **Don't** use a type colour as decoration or a section background.
- **Don't** use emoji or Unicode glyphs as icons; icons are Lucide, 1.75–2 px strokes.
- **Don't** add a coloured stripe to the side of a card, list item or panel.
- **Don't** show a disabled control without saying when it arrives ("Mood picks are coming soon").
