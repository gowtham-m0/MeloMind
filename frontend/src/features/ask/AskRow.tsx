import { Loader2, X } from "lucide-react";

import type { FeedItem } from "@/shared/api/feed";

import { AgentLog } from "../feed/AgentLog";
import { FeedRowView } from "../feed/FeedRowView";

import { useAsk } from "./useAsk";

interface AskRowProps {
  onOpen: (item: FeedItem) => void;
  onLike: (item: FeedItem) => void;
  onSave: (item: FeedItem) => void;
  onDismiss: (item: FeedItem) => void;
  onOpened?: (item: FeedItem, platform: string) => void;
}

/** The agent's extra row at the top of the feed: a live log while it works, then the row with a
 * dismiss button. Renders nothing when there's no request. */
export function AskRow(actions: AskRowProps) {
  const { running, label, run, row, dismiss } = useAsk();

  if (running) {
    return (
      <section
        aria-label={`Building ${label}`}
        className="rise-in rounded-2xl border border-primary/40 bg-primary-tint/50 p-5"
      >
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Loader2 className="size-5 animate-spin text-primary-ink" aria-hidden />
          Building {label.toLowerCase()}…
        </h2>
        <div className="mt-3">
          <AgentLog run={run} compact label="How the agent is building this row" />
        </div>
      </section>
    );
  }
  if (!row) {
    return null;
  }
  return (
    <div className="rise-in relative">
      <FeedRowView row={row} {...actions} />
      <button
        type="button"
        onClick={dismiss}
        aria-label={`Dismiss ${row.title}`}
        className="absolute top-0 right-0 inline-flex h-9 items-center gap-1 rounded-full bg-surface-2 px-3 text-sm font-semibold text-body transition-colors hover:bg-line hover:text-ink md:right-[88px]"
      >
        <X className="size-4" /> Dismiss
      </button>
    </div>
  );
}
