import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "cn";
import { Check, MapPin, Pencil, RotateCw, Sparkles, Trash2, X } from "lucide-react";
import { useState } from "react";

import { updateEntry, type JournalEntry, type JournalLink } from "@/shared/api/journal";
import { Button } from "@/shared/ui/button";
import { Thumb } from "@/shared/ui/thumb";
import type { ItemType } from "@/shared/ui/types";

import { AgentLog } from "../feed/AgentLog";
import { useItemParam } from "../item-detail/useItemParam";

import { journalKey, useDeleteEntry, useLinkDecisions, useLinkRun } from "./hooks";

const KIND_LABELS: Record<string, string> = {
  artist: "artist",
  song: "song",
  movie: "film",
  tv_show: "show",
  book: "book",
  place: "place",
};

function thumbType(kind: string): ItemType | null {
  return kind === "place" || kind === "entry" ? null : (kind as ItemType);
}

/** A linked item's picture: its image or the type's tile; a pin for a place. */
function TargetThumb({ link, size }: { link: JournalLink; size: string }) {
  const type = thumbType(link.target.kind);
  if (type === null) {
    return (
      <span
        className={cn(
          "grid shrink-0 place-items-center rounded-full bg-surface-3 text-muted",
          size,
        )}
      >
        <MapPin className="size-4" />
      </span>
    );
  }
  return (
    <Thumb
      src={link.target.image_url}
      title={link.target.title}
      type={type}
      aspect="square"
      round={type === "artist" || type === "song"}
      className={cn("shrink-0", size)}
    />
  );
}

interface EntryCardProps {
  profileId: string;
  entry: JournalEntry;
  runId: string | null;
  onRun: (entryId: string, runId: string) => void;
  onSuggestAgain: (entryId: string) => void;
}

/** One entry: its text, the items it's linked to, and the agent's suggestions to confirm. */
export function EntryCard({ profileId, entry, runId, onRun, onSuggestAgain }: EntryCardProps) {
  const queryClient = useQueryClient();
  const run = useLinkRun(profileId, runId);
  const { decide, confirmEvery } = useLinkDecisions(profileId);
  const remove = useDeleteEntry(profileId);
  const { open } = useItemParam();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(entry.text);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const save = useMutation({
    mutationFn: () => updateEntry(profileId, entry.id, { text: draft.trim() }),
    onSuccess: (updated) => {
      queryClient.setQueryData<JournalEntry[]>(journalKey(profileId), (entries) =>
        (entries ?? []).map((known) => (known.id === updated.id ? updated : known)),
      );
      setEditing(false);
      if (updated.link_run_id) {
        onRun(updated.id, updated.link_run_id);
      }
    },
  });

  const linking = run.data?.status === "running" || (runId !== null && run.isPending);
  const failed = run.data?.status === "failed";
  const fromMemory = run.data?.status === "done" && run.data.result?.ai_read === false;

  return (
    <article className="rounded-2xl border border-hairline bg-surface p-4 shadow-soft md:p-5">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          {entry.mood && (
            <span className="mb-2 inline-flex h-7 items-center rounded-full bg-primary-tint px-3 text-[13px] font-semibold text-primary-ink capitalize">
              {entry.mood}
            </span>
          )}
          {editing ? (
            <div className="flex flex-col gap-2">
              <label className="sr-only" htmlFor={`edit-${entry.id}`}>
                Edit entry
              </label>
              <textarea
                id={`edit-${entry.id}`}
                value={draft}
                maxLength={5000}
                rows={4}
                onChange={(event) => setDraft(event.target.value)}
                className="w-full resize-y rounded-xl border border-primary bg-surface p-3 text-base leading-relaxed text-ink"
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={() => save.mutate()}
                  disabled={!draft.trim() || save.isPending}
                >
                  {save.isPending ? "Saving…" : "Save"}
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setDraft(entry.text);
                    setEditing(false);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <p className="text-[17px] leading-relaxed whitespace-pre-wrap text-ink">{entry.text}</p>
          )}
        </div>
        {!editing && (
          <div className="flex shrink-0 gap-1">
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="Edit entry"
              onClick={() => setEditing(true)}
            >
              <Pencil className="size-4" />
            </Button>
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label="Delete entry"
              onClick={() => setConfirmingDelete(true)}
            >
              <Trash2 className="size-4" />
            </Button>
          </div>
        )}
      </div>

      {confirmingDelete && (
        <div
          role="alertdialog"
          aria-label="Delete this entry?"
          className="mt-3 flex flex-wrap items-center gap-3 rounded-xl bg-film/6 p-3"
        >
          <p className="flex-1 text-sm text-body">
            Delete this entry? Its links leave your taste too.
          </p>
          <Button
            size="sm"
            variant="dark"
            onClick={() => remove.mutate(entry.id)}
            disabled={remove.isPending}
          >
            Delete
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setConfirmingDelete(false)}>
            Keep it
          </Button>
        </div>
      )}

      {entry.links.length > 0 && (
        <ul aria-label="Linked to" className="mt-4 flex flex-wrap gap-2">
          {entry.links.map((link) => {
            const opensDetail = link.target.qloo_id !== null && link.target.kind !== "place";
            const body = (
              <>
                <TargetThumb link={link} size="size-8" />
                <span className="truncate">{link.target.title}</span>
              </>
            );
            return (
              <li key={link.id} className="settle-in max-w-full">
                {opensDetail ? (
                  <button
                    type="button"
                    onClick={() => open(link.target.qloo_id ?? "")}
                    className="flex h-11 max-w-full items-center gap-2 rounded-full border border-line bg-surface py-1 pr-4 pl-1 text-sm font-medium text-ink transition-colors hover:border-[#c9c9c9]"
                  >
                    {body}
                  </button>
                ) : (
                  <span className="flex h-11 max-w-full items-center gap-2 rounded-full border border-line bg-surface py-1 pr-4 pl-1 text-sm font-medium text-ink">
                    {body}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {linking && (
        <div className="mt-4 rounded-xl bg-surface-2 p-3">
          <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-ink">
            <Sparkles className="size-4 text-primary-ink" /> Finding what you mentioned…
          </p>
          <AgentLog run={run.data ?? null} compact label="How the agent read your entry" />
        </div>
      )}

      {failed && entry.suggestions.length === 0 && (
        <div className="mt-4 flex flex-wrap items-center gap-3 rounded-xl bg-surface-2 p-3">
          <p className="flex-1 text-sm text-body">Couldn't suggest links this time.</p>
          <Button size="sm" variant="secondary" onClick={() => onSuggestAgain(entry.id)}>
            <RotateCw /> Try again
          </Button>
        </div>
      )}

      {entry.suggestions.length > 0 && (
        <div className="mt-4 rounded-xl border border-dashed border-primary/50 bg-primary-tint/40 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-sm font-semibold text-ink">
              Did you mean these?{" "}
              <span className="font-normal text-muted">
                Only what you confirm shapes your feed.
              </span>
            </p>
            {entry.suggestions.length > 1 && (
              <Button size="sm" variant="secondary" onClick={() => void confirmEvery(entry.id)}>
                <Check /> Confirm all
              </Button>
            )}
          </div>
          {fromMemory && (
            <p className="mt-1 text-xs text-muted">
              The AI reader was off, so these are things you already love.
            </p>
          )}
          <ul className="mt-3 flex flex-col gap-2">
            {entry.suggestions.map((link) => (
              <li
                key={link.id}
                className="flex items-center gap-3 rounded-xl bg-surface p-2 shadow-soft"
              >
                <TargetThumb link={link} size="size-11" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[15px] font-semibold text-ink">
                    {link.target.title}
                    <span className="font-normal text-muted">
                      {" "}
                      · {KIND_LABELS[link.target.kind] ?? link.target.kind}
                    </span>
                  </span>
                  <span className="block truncate text-sm text-muted">
                    {link.target.creator ? `By ${link.target.creator}. ` : ""}
                    {link.reason}
                  </span>
                </span>
                <Button
                  size="icon-sm"
                  aria-label={`Confirm ${link.target.title}`}
                  onClick={() => void decide(entry.id, link, "confirmed")}
                >
                  <Check className="size-4" />
                </Button>
                <Button
                  size="icon-sm"
                  variant="secondary"
                  aria-label={`Not ${link.target.title}`}
                  onClick={() => void decide(entry.id, link, "rejected")}
                >
                  <X className="size-4" />
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  );
}
