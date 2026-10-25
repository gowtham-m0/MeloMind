import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "react-router";

import { Composer } from "@/features/journal/Composer";
import { EntryCard } from "@/features/journal/EntryCard";
import { useJournal, useSuggestAgain } from "@/features/journal/hooks";
import type { JournalEntry } from "@/shared/api/journal";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";

function dayLabel(iso: string): string {
  const day = new Date(`${iso}T00:00:00`);
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const days = Math.round((startOfToday.getTime() - day.getTime()) / 86_400_000);
  if (days === 0) {
    return "Today";
  }
  if (days === 1) {
    return "Yesterday";
  }
  return day.toLocaleDateString(undefined, {
    weekday: "short",
    day: "numeric",
    month: "short",
    year: day.getFullYear() === now.getFullYear() ? undefined : "numeric",
  });
}

function byDay(entries: JournalEntry[]): [string, JournalEntry[]][] {
  const groups = new Map<string, JournalEntry[]>();
  for (const entry of entries) {
    groups.set(entry.date, [...(groups.get(entry.date) ?? []), entry]);
  }
  return [...groups.entries()];
}

/** The journal: write or speak an entry, confirm what the agent spotted, and look back by day. */
export function JournalPage() {
  const { profileId = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const journal = useJournal(profileId);
  const suggestAgain = useSuggestAgain(profileId);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const [runs, setRuns] = useState<Record<string, string>>({});

  const compose = params.get("compose") !== null;
  useEffect(() => {
    if (compose) {
      textRef.current?.focus();
      setParams(
        (current) => {
          const next = new URLSearchParams(current);
          next.delete("compose");
          return next;
        },
        { replace: true },
      );
    }
  }, [compose, setParams]);

  const track = (entryId: string, runId: string) =>
    setRuns((current) => ({ ...current, [entryId]: runId }));

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-8">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">Journal</h1>
        <p className="mt-1 text-body">
          Write about your day. The agent spots the music, films, shows and books you mention, and
          you decide what counts.
        </p>
      </div>

      <Composer
        profileId={profileId}
        textRef={textRef}
        onSaved={(entry) => entry.link_run_id && track(entry.id, entry.link_run_id)}
      />

      <section aria-labelledby="timeline-title" className="flex flex-col gap-6">
        <h2 id="timeline-title" className="sr-only">
          Your entries
        </h2>
        {journal.isPending ? (
          <div className="flex flex-col gap-4">
            <Skeleton className="h-36 w-full" />
            <Skeleton className="h-36 w-full" />
          </div>
        ) : journal.isError ? (
          <ErrorState error={journal.error} onRetry={() => void journal.refetch()} />
        ) : journal.data.length === 0 ? (
          <EmptyState title="Your first entry starts here">
            Mention a song, a film or a book you loved today. The agent will suggest links for you
            to confirm.
          </EmptyState>
        ) : (
          byDay(journal.data).map(([day, entries]) => (
            <div key={day} className="flex flex-col gap-3">
              <h3 className="font-sans text-sm font-semibold tracking-wide text-muted uppercase">
                {dayLabel(day)}
              </h3>
              {entries.map((entry) => (
                <EntryCard
                  key={entry.id}
                  profileId={profileId}
                  entry={entry}
                  runId={runs[entry.id] ?? null}
                  onRun={track}
                  onSuggestAgain={(entryId) =>
                    suggestAgain.mutate(entryId, {
                      onSuccess: (updated) =>
                        updated.link_run_id && track(updated.id, updated.link_run_id),
                    })
                  }
                />
              ))}
            </div>
          ))
        )}
      </section>
    </div>
  );
}
