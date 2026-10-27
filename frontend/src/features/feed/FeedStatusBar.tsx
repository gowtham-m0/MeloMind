import { cn } from "cn";
import { ListTree, RefreshCw } from "lucide-react";

import type { AgentRun, Feed } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { SourceBadge } from "@/shared/ui/chip";

interface FeedStatusBarProps {
  feed: Feed;
  building: boolean;
  run: AgentRun | null;
  onRefresh: () => void;
  onShowLog: () => void;
}

/** One line above the feed: what changed since last time, or that the agent is rebuilding, with
 * a refresh button that turns amber once your taps have made the feed out of date. */
export function FeedStatusBar({ feed, building, run, onRefresh, onShowLog }: FeedStatusBarProps) {
  const lastStep = run?.steps.at(-1)?.message;
  const source = feed.hero?.source ?? feed.rows[0]?.items[0]?.source ?? "qloo_live";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p aria-live="polite" className="min-w-0 flex-1 text-[15px] text-body">
        {building ? (
          <span className="flex min-w-0 items-center gap-2">
            <RefreshCw className="size-4 shrink-0 animate-spin text-primary-ink" aria-hidden />
            <span className="truncate">{lastStep ?? "Rebuilding your feed…"}</span>
          </span>
        ) : (
          feed.summary
        )}
      </p>
      <div className="flex w-full flex-wrap items-center gap-2 sm:w-auto">
        <SourceBadge source={source} />
        <Button variant="ghost" size="sm" onClick={onShowLog} className="px-2.5">
          <ListTree /> <span className="sm:hidden">How</span>
          <span className="hidden sm:inline">How it was built</span>
        </Button>
        <Button
          variant={feed.stale ? "primary" : "secondary"}
          size="sm"
          onClick={onRefresh}
          disabled={building}
          className={cn(
            "ml-auto sm:ml-0",
            feed.stale && !building && "shadow-[0_0_0_4px_#e8a83833]",
          )}
        >
          <RefreshCw className={cn(building && "animate-spin")} />
          {feed.stale ? (
            <>
              <span className="sm:hidden">New picks</span>
              <span className="hidden sm:inline">Refresh for new picks</span>
            </>
          ) : (
            "Refresh"
          )}
        </Button>
      </div>
    </div>
  );
}
