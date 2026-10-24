# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Anyone, anywhere, of any age, who has taste across music, films, TV and books and is tired of every app only knowing its own catalogue. They open MeloMind the way they open YouTube, Spotify or Netflix: to find the next thing to play, watch or read, and to see why it was picked. Secondary audience during October 2026: Qloo Agentic Hackathon judges trying the demo for about five minutes.

## Product Purpose

MeloMind is a personal taste dashboard: one home screen of recommendations across music, films, TV and books, built by an AI agent on Qloo's taste graph. Every card has a thumbnail, a one-line reason, and a link that opens it where it lives (YouTube or Spotify, Netflix or JustWatch, Google Books or Goodreads). Likes, saves, opens and "not interested" change the next feed, and the agent log says what changed. An everyday journal (written or spoken) lets the agent spot what you mention and fold it into your taste once you confirm it.

Success: a new user gets a feed that feels like theirs within a minute, understands why each pick is there, and sees it change after a few taps.

## Positioning

Cross-domain taste with reasons. Streaming apps recommend only their own catalogue; MeloMind links across types ("you love this band, so try this film, this show, this book") using Qloo's cross-domain graph, and explains every pick from the signal behind it. Nothing is invented: every pick is a Qloo result, and the agent's steps are visible.

## Operating Context

- Web app, phone first, then tablet and desktop. Signed in anonymously for the demo, with Netflix-style profiles.
- Home feed is a saved snapshot that opens instantly; refreshing runs the agent in the background (about 20–30 seconds) with a live log.
- Links leave the app to the platform where the item lives.
- Demo profiles: Aanya (indie and sci-fi, India) and Leo (60s classics, US).

## Capabilities and Constraints

- Four types only: artists, films, TV shows, books. Qloo has no songs, so music cards are artists.
- Thumbnails come from Qloo image URLs (or Open Library covers for books); never stored or re-hosted.
- Platform links are honest: "Search on Netflix" unless a direct ID exists ("Open on Netflix").
- "Not interested" items never return until undone.
- Journal entries are private, never sent to Qloo; voice audio is discarded after transcription.
- Stack: React 19, Vite, TypeScript, Tailwind, shadcn/ui, TanStack Query; FastAPI backend.

## Brand Commitments

- Name: MeloMind. Tagline: "Your personal culture companion".
- Voice: bold and playful. Punchy, energetic, witty, with personality, but always clear and honest; never misleading about where a link goes.
- Binding layout reference: the user's mockup `image.png` (left sidebar, top search, hero banner, category tiles, rows, right rail with vibe chips, quick actions and cross-culture picks). Its dark purple colours are not the brand.
- Binding look: light and airy, inspired by yuzuhire.com, with the tokens in `CLAUDE.md` ("Design system").

## Evidence on Hand

- Live Qloo data with images for every entity, Spotify/Netflix/IMDb/Goodreads IDs.
- Hand-written demo fixtures (labelled "Demo data").
- No testimonials, users, metrics or press exist. Do not fabricate any.

## Product Principles

1. Every pick earns its place: it shows why, and where to find it.
2. Taste is cross-domain: always show a bridge between music, screen and page.
3. The feed visibly learns: a few taps should change what you see, and the app says so.
4. Honest by default: no invented picks, no fake "watch now", no hidden data use.
5. Fast to feel personal: under a minute from landing to a feed that feels like yours.

## Accessibility & Inclusion

WCAG 2.2 AA: contrast, full keyboard use with visible focus, 44 px tap targets, `prefers-reduced-motion` respected, `aria-live` on the agent log and refresh toasts. All ages, so text stays at least 16 px and copy stays plain even when playful.
