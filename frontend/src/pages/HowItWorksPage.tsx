import { ArrowLeft, BookOpen, Link2, Lock, Search, Sparkles, Wand2 } from "lucide-react";
import type { ReactNode } from "react";
import { Link } from "react-router";

import { Logo } from "@/shared/ui/logo";

const WORKFLOWS = [
  {
    title: "Build your feed",
    body: "Reads your favourites and likes, researches with Qloo, fills the rows, then checks every pick against your rules.",
  },
  {
    title: "Find a favourite",
    body: "Turns a name, a song or a half-remembered line into a real match, and asks you to confirm it.",
  },
  {
    title: "Read your journal",
    body: "Spots the artists, films, shows and books you mention and proposes them. Nothing counts until you tap ✓.",
  },
];

const TOOLS: { name: string; does: string }[] = [
  { name: "search_entities", does: "Qloo /search: names to artists, films, shows and books" },
  { name: "find_tags", does: "Qloo /v2/tags: words like “lighter” to real tags" },
  { name: "get_insights", does: "Qloo /v2/insights: what you'd like, minus what you hid" },
  { name: "compare_tastes", does: "Qloo compare: the tags two people share" },
  { name: "find_journal_links", does: "Items already linked in your journal" },
];

const QLOO_CALLS = [
  "Search turns a name into an entity ID with its image.",
  "Insights takes your favourites and likes as signals and returns what people with that taste love.",
  "Tags let the agent steer by feeling: chill, feel-good, 90s.",
  "Compare finds the tags two tastes share, for Taste match.",
];

function Section({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="flex items-center gap-3 text-[26px] font-semibold">
        <span className="grid size-10 place-items-center rounded-xl bg-primary-tint text-primary-ink">
          {icon}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

/** How MeloMind works, in plain words: one agent, its tools, the Qloo calls, honest links and
 * privacy. Public, so it can be read before signing in. */
export function HowItWorksPage() {
  return (
    <div className="min-h-dvh bg-surface">
      <header className="mx-auto flex max-w-4xl items-center justify-between px-5 py-5 md:px-8">
        <Logo />
        <Link
          to="/"
          className="inline-flex h-11 items-center gap-2 rounded-lg px-3 text-[15px] font-semibold text-ink hover:bg-surface-2"
        >
          <ArrowLeft className="size-4" /> Back
        </Link>
      </header>
      <main className="mx-auto flex max-w-4xl flex-col gap-14 px-5 pt-6 pb-20 md:px-8">
        <div className="flex flex-col gap-3">
          <h1 className="max-w-[18ch] text-[40px] leading-[1.05] font-semibold text-balance md:text-[56px]">
            One agent. Your taste. Every pick explained.
          </h1>
          <p className="max-w-prose text-lg text-body">
            MeloMind never invents a recommendation. Qloo's taste graph finds what you'd love; the
            agent decides what to ask it, and tells you why each pick is there.
          </p>
        </div>

        <Section icon={<Wand2 className="size-5" />} title="The agent">
          <p className="max-w-prose text-body">
            There's a single agent with three jobs. Code sets the order of each job; the AI decides
            only which questions to ask Qloo.
          </p>
          <ol className="flex flex-col divide-y divide-hairline border-y border-hairline">
            {WORKFLOWS.map((workflow) => (
              <li
                key={workflow.title}
                className="grid gap-1 py-4 sm:grid-cols-[220px_1fr] sm:gap-6"
              >
                <h3 className="text-lg font-semibold">{workflow.title}</h3>
                <p className="text-[15px] text-body">{workflow.body}</p>
              </li>
            ))}
          </ol>
          <div className="rounded-xl bg-surface-2 p-5">
            <h3 className="text-base font-semibold">Its tools</h3>
            <ul className="mt-3 flex flex-col gap-2">
              {TOOLS.map((tool) => (
                <li
                  key={tool.name}
                  className="flex flex-col gap-0.5 text-[15px] sm:flex-row sm:gap-3"
                >
                  <code className="shrink-0 font-mono text-sm font-semibold text-ink sm:w-44">
                    {tool.name}
                  </code>
                  <span className="text-body">{tool.does}</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-sm text-muted">
              Every call is written to the agent log, in plain English, so you can read how a feed
              was built.
            </p>
          </div>
        </Section>

        <Section icon={<Search className="size-5" />} title="What we ask Qloo">
          <ul className="flex max-w-prose flex-col gap-2.5">
            {QLOO_CALLS.map((line) => (
              <li key={line} className="flex gap-3 text-body">
                <Sparkles className="mt-1 size-4 shrink-0 text-primary-ink" aria-hidden />
                {line}
              </li>
            ))}
          </ul>
          <p className="max-w-prose text-body">
            Qloo has no songs, so music picks are artists. Songs on a card are that artist's top
            tracks, looked up in Apple's iTunes catalogue. They're a lookup, never a recommender.
          </p>
        </Section>

        <Section icon={<Link2 className="size-5" />} title="Honest links">
          <p className="max-w-prose text-body">
            A button that says <strong>Search on Netflix</strong> opens a search, because we can't
            promise it's there. <strong>Watch on</strong> and <strong>Listen on</strong> only appear
            when we have a direct link to that exact title. Nothing plays until you tap.
          </p>
        </Section>

        <Section icon={<Lock className="size-5" />} title="Privacy">
          <ul className="flex max-w-prose flex-col gap-2.5 text-body">
            <li className="flex gap-3">
              <BookOpen className="mt-1 size-4 shrink-0 text-primary-ink" aria-hidden />
              Your journal is private to your profile. It's never sent to Qloo, which only ever sees
              entity IDs and tags.
            </li>
            <li className="flex gap-3">
              <BookOpen className="mt-1 size-4 shrink-0 text-primary-ink" aria-hidden />
              Voice notes are turned into text and the audio is thrown away.
            </li>
            <li className="flex gap-3">
              <BookOpen className="mt-1 size-4 shrink-0 text-primary-ink" aria-hidden />
              Anything the AI works out is a proposal. It only shapes your feed once you confirm it.
            </li>
            <li className="flex gap-3">
              <BookOpen className="mt-1 size-4 shrink-0 text-primary-ink" aria-hidden />
              Something marked “not interested” never comes back until you undo it in Settings. You
              can delete a profile and its journal at any time.
            </li>
          </ul>
        </Section>
      </main>
    </div>
  );
}
