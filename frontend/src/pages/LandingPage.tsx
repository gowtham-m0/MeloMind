import { ArrowRight, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { useMutation } from "@tanstack/react-query";

import { ensureSignedIn, useTryDemo } from "@/features/session/auth";
import { useAccount } from "@/features/session/useAccount";
import { useSession } from "@/features/session/useSession";
import { Button } from "@/shared/ui/button";
import { Logo } from "@/shared/ui/logo";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

const EXAMPLE: { type: ItemType; title: string; note: string }[] = [
  { type: "artist", title: "Arctic Monkeys", note: "you love them" },
  { type: "movie", title: "Inception", note: "same restless energy" },
  { type: "tv_show", title: "Black Mirror", note: "sharp and a little dark" },
  { type: "book", title: "The Martian", note: "big-idea sci-fi" },
];

/** The signed-out front door: what MeloMind does, shown as a taste thread, and two ways in. */
export function LandingPage() {
  const { session } = useSession();
  const { isGuest } = useAccount();
  const tryDemo = useTryDemo();
  const navigate = useNavigate();
  const startFresh = useMutation({
    mutationFn: ensureSignedIn,
    onSuccess: () => navigate("/profiles/new"),
  });
  const error = tryDemo.error ?? startFresh.error;

  return (
    <div className="min-h-dvh bg-surface">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-5 py-5 md:px-8">
        <Logo />
        <div className="flex items-center gap-2">
          {session && (
            <Button asChild variant="secondary" size="sm">
              <Link to="/profiles">Your profiles</Link>
            </Button>
          )}
          {!(session && !isGuest) && (
            <Button asChild variant={session ? "ghost" : "secondary"} size="sm">
              <Link to="/sign-in">{isGuest ? "Save your profiles" : "Sign in"}</Link>
            </Button>
          )}
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-12 px-5 pt-6 pb-20 md:grid-cols-[1.1fr_1fr] md:px-8 md:pt-16">
        <section className="flex flex-col gap-6">
          <h1 className="text-[44px] leading-[1.02] font-semibold md:text-[68px]">
            Your taste,
            <br />
            in <span className="text-primary">one</span> home screen.
          </h1>
          <p className="max-w-[46ch] text-lg leading-relaxed text-body">
            Music, films, TV and books that actually get you, each with the reason it's here and a
            tap to open it on Spotify, Netflix, Goodreads and the rest. Built by an AI agent on
            Qloo's taste graph.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" onClick={() => tryDemo.mutate()} disabled={tryDemo.isPending}>
              <Sparkles /> {tryDemo.isPending ? "Setting up the demo…" : "Try the demo"}
            </Button>
            <Button
              size="lg"
              variant="secondary"
              onClick={() => startFresh.mutate()}
              disabled={startFresh.isPending}
            >
              Start fresh <ArrowRight />
            </Button>
          </div>
          {error && (
            <p role="alert" className="text-danger">
              {error.message}
            </p>
          )}
          <p className="text-sm text-muted">
            No sign-up needed to look around. Sign in later to keep what you build.
          </p>
        </section>

        <section
          aria-label="Example: one taste, followed across four kinds of thing"
          className="rise-in"
        >
          <ol className="relative flex flex-col gap-3 rounded-2xl border border-hairline bg-surface p-5 shadow-lift md:p-7">
            {EXAMPLE.map((step, index) => {
              const meta = TYPE_META[step.type];
              return (
                <li key={step.title} className="relative flex items-center gap-4">
                  {index > 0 && (
                    <span
                      aria-hidden
                      className="thread-segment absolute -top-[30px] left-[21px] h-[34px] w-[3px] rounded-full"
                      style={{
                        background: `linear-gradient(${TYPE_META[EXAMPLE[index - 1].type].color}, ${meta.color})`,
                        animationDelay: `${index * 160}ms`,
                      }}
                    />
                  )}
                  <span
                    className={`thread-node grid size-[45px] shrink-0 place-items-center rounded-full ${meta.tint}`}
                    style={{ animationDelay: `${index * 160}ms` }}
                  >
                    <meta.icon className={`size-5 ${meta.text}`} />
                  </span>
                  <span className="min-w-0 flex-1 rounded-xl bg-surface-2 px-4 py-3">
                    <span
                      className={`block text-xs font-semibold tracking-wide uppercase ${meta.text}`}
                    >
                      {index === 0 ? "You like" : meta.verb}
                    </span>
                    <span className="block font-display text-xl font-semibold text-ink">
                      {step.title}
                    </span>
                    <span className="block text-sm text-muted">{step.note}</span>
                  </span>
                </li>
              );
            })}
          </ol>
          <p className="mt-3 text-center text-sm text-muted">
            An example thread. Yours is built from your taste.
          </p>
        </section>
      </main>
    </div>
  );
}
