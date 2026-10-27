import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, HelpCircle, Sparkles } from "lucide-react";
import { useId, useState } from "react";

import { getRun } from "@/shared/api/feed";
import type { FavouriteKind } from "@/shared/api/profiles";
import { resolveFavourite, type ResolveProposal, type TextFavourite } from "@/shared/api/taste";
import { Button } from "@/shared/ui/button";
import { TypeChip } from "@/shared/ui/chip";
import { Thumb } from "@/shared/ui/thumb";
import type { ItemType } from "@/shared/ui/types";

import { AgentLog } from "../feed/AgentLog";
import { useAddFavourite } from "../profiles/hooks";

const RUN_POLL_MS = 1000;
const TEXT_MAX = 300;

interface RunResult {
  proposals?: ResolveProposal[];
  question?: string | null;
  text_favourite?: TextFavourite | null;
}

/**
 * "Type a line you remember": a name, a song, a lyric or a description. The agent climbs its
 * hint ladder and proposes up to three matches; you confirm one, or add a hint and try again.
 * The box clears afterwards, and what was typed is never shown again or saved.
 */
export function RememberBox({ profileId, onAdded }: { profileId: string; onAdded?: () => void }) {
  const inputId = useId();
  const [text, setText] = useState("");
  const [hint, setHint] = useState("");
  const [kind, setKind] = useState<FavouriteKind | undefined>(undefined);
  const [runId, setRunId] = useState<string | null>(null);
  const [added, setAdded] = useState<string | null>(null);
  const [saveFailed, setSaveFailed] = useState(false);
  const addFavourite = useAddFavourite(profileId);

  const start = useMutation({
    mutationFn: (withHint: boolean) =>
      resolveFavourite(profileId, {
        text: text.trim(),
        kind,
        hint: withHint && hint.trim() ? hint.trim() : undefined,
      }),
    onSuccess: ({ agent_run_id }) => {
      setAdded(null);
      setSaveFailed(false);
      setRunId(agent_run_id);
    },
  });

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId ?? ""),
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? RUN_POLL_MS : false),
  });

  const status = run.data?.status;
  const result = (run.data?.result ?? {}) as RunResult;
  const proposals = status === "done" ? (result.proposals ?? []) : [];
  const busy = start.isPending || status === "running" || (runId !== null && run.isPending);

  function reset(name: string) {
    setText("");
    setHint("");
    setRunId(null);
    setAdded(name);
    onAdded?.();
  }

  async function confirm(proposal: ResolveProposal) {
    setSaveFailed(false);
    try {
      await addFavourite.mutateAsync({
        name: proposal.name,
        kind: proposal.kind,
        entity_id: proposal.entity_id,
        image_url: proposal.image_url,
        song_title: proposal.song_title,
      });
    } catch {
      setSaveFailed(true);
      return;
    }
    reset(proposal.song_title ? `${proposal.song_title} by ${proposal.name}` : proposal.name);
  }

  async function keepAsText(favourite: TextFavourite) {
    setSaveFailed(false);
    try {
      await addFavourite.mutateAsync({
        name: favourite.name,
        kind: favourite.kind,
        song_title: favourite.song_title,
      });
    } catch {
      setSaveFailed(true);
      return;
    }
    reset(favourite.song_title ?? favourite.name);
  }

  return (
    <section
      aria-labelledby={`${inputId}-title`}
      className="rounded-2xl border border-hairline bg-surface-2/70 p-4 md:p-5"
    >
      <h2 id={`${inputId}-title`} className="flex items-center gap-2 text-lg font-semibold">
        <Sparkles className="size-[18px] text-primary-ink" /> Type a line you remember
      </h2>
      <p className="mt-0.5 text-sm text-muted">
        A name, a song, a lyric or a scene. The agent works out what you mean.
      </p>
      <form
        className="mt-3 flex flex-col gap-2 sm:flex-row"
        onSubmit={(event) => {
          event.preventDefault();
          if (text.trim()) {
            start.mutate(false);
          }
        }}
      >
        <label htmlFor={inputId} className="sr-only">
          What you remember
        </label>
        <input
          id={inputId}
          value={text}
          maxLength={TEXT_MAX}
          onChange={(event) => setText(event.target.value)}
          placeholder="“that song about heat waves”, or a line from it…"
          className="h-12 min-w-0 flex-1 rounded-[10px] border border-transparent bg-surface px-4 text-base text-ink placeholder:text-muted focus:border-primary"
        />
        <label className="sr-only" htmlFor={`${inputId}-kind`}>
          It's a
        </label>
        <select
          id={`${inputId}-kind`}
          value={kind ?? ""}
          onChange={(event) =>
            setKind(event.target.value ? (event.target.value as FavouriteKind) : undefined)
          }
          className="h-12 rounded-[10px] border border-line bg-surface px-3 text-[15px] text-ink"
        >
          <option value="">Anything</option>
          <option value="song">A song</option>
          <option value="artist">An artist</option>
          <option value="movie">A film</option>
          <option value="tv_show">A TV show</option>
          <option value="book">A book</option>
        </select>
        <Button type="submit" size="lg" disabled={!text.trim() || busy}>
          {busy ? "Looking…" : "Find it"}
        </Button>
      </form>

      <div aria-live="polite">
        {added && (
          <p className="settle-in mt-3 flex items-center gap-2 text-sm font-semibold text-book-ink">
            <Check className="size-4" /> Added {added} to your favourites.
          </p>
        )}
        {busy && runId && (
          <div className="mt-3">
            <AgentLog run={run.data ?? null} compact label="How the agent looked it up" />
          </div>
        )}
        {(start.isError || status === "failed") && (
          <p role="alert" className="mt-3 text-sm text-danger">
            Couldn't look that up just now. Try again.
          </p>
        )}
        {saveFailed && (
          <p role="alert" className="mt-3 text-sm text-danger">
            Couldn't save that favourite. Try again.
          </p>
        )}

        {proposals.length > 0 && (
          <ul className="mt-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
            {proposals.map((proposal) => (
              <li key={`${proposal.entity_id}-${proposal.kind}`}>
                <button
                  type="button"
                  onClick={() => void confirm(proposal)}
                  disabled={addFavourite.isPending}
                  className="lift flex w-full items-center gap-3 rounded-xl bg-surface p-2 text-left shadow-soft"
                >
                  <Thumb
                    src={proposal.image_url}
                    title={proposal.name}
                    type={proposal.type as ItemType}
                    aspect="square"
                    round={proposal.type === "artist"}
                    className="size-14 shrink-0"
                  />
                  <span className="min-w-0">
                    <TypeChip
                      type={(proposal.kind === "song" ? "song" : proposal.type) as ItemType}
                    />
                    <span className="block truncate font-semibold text-ink">
                      {proposal.song_title ? `${proposal.song_title} · ` : ""}
                      {proposal.name}
                    </span>
                    <span className="block truncate text-xs text-muted">
                      {proposal.year ? `${proposal.year} · ` : ""}
                      {proposal.why}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {status === "needs_hint" && (
          <div className="mt-4 rounded-xl bg-surface p-3 shadow-soft">
            <p className="flex items-center gap-2 font-semibold text-ink">
              <HelpCircle className="size-[18px] text-primary-ink" />
              {result.question ?? "Can you add a hint?"}
            </p>
            <form
              className="mt-2 flex flex-col gap-2 sm:flex-row"
              onSubmit={(event) => {
                event.preventDefault();
                if (hint.trim()) {
                  start.mutate(true);
                }
              }}
            >
              <label className="sr-only" htmlFor={`${inputId}-hint`}>
                Your hint
              </label>
              <input
                id={`${inputId}-hint`}
                value={hint}
                maxLength={100}
                onChange={(event) => setHint(event.target.value)}
                placeholder="The singer, the film or the year"
                className="h-11 min-w-0 flex-1 rounded-[10px] border border-line bg-surface px-3 text-base text-ink"
              />
              <Button type="submit" variant="secondary" disabled={!hint.trim() || busy}>
                Try again
              </Button>
              {result.text_favourite && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => void keepAsText(result.text_favourite as TextFavourite)}
                >
                  Keep “{result.text_favourite.song_title ?? result.text_favourite.name}” as text
                </Button>
              )}
            </form>
          </div>
        )}
      </div>
    </section>
  );
}
