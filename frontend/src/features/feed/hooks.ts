import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/shared/api/client";
import {
  getFeed,
  getRun,
  listExclusions,
  refreshFeed,
  removeExclusion,
  sendFeedback,
  type AgentRun,
  type Feed,
  type FeedItem,
} from "@/shared/api/feed";
import { useToast } from "@/shared/ui/toast";

const RUN_POLL_MS = 1000;

/** Profiles whose feed was already rebuilt since this page loaded, so a reload refreshes the
 * recommendations once and moving around the app doesn't rebuild them again. */
const rebuiltThisLoad = new Set<string>();

export const feedKey = (profileId: string) => ["feed", profileId] as const;

/** The newest finished feed, or null while there is none yet. */
async function loadFeed(profileId: string): Promise<Feed | null> {
  try {
    return await getFeed(profileId);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return null;
    }
    throw error;
  }
}

/** The cached feed for read-only views (the sidebar's taste chips). Never starts a build. */
export function useFeedSnapshot(profileId: string) {
  return useQuery({ queryKey: feedKey(profileId), queryFn: () => loadFeed(profileId) });
}

/**
 * The feed and its builds. With no feed yet, it starts a build straight away; while a build runs,
 * it polls the agent run (for the live log) and swaps in the new feed when the run finishes.
 */
export function useFeed(profileId: string) {
  const queryClient = useQueryClient();
  const [runId, setRunId] = useState<string | null>(null);

  const feed = useQuery({ queryKey: feedKey(profileId), queryFn: () => loadFeed(profileId) });

  const refresh = useMutation({
    mutationFn: () => refreshFeed(profileId),
    onSuccess: (building) => setRunId(building.agent_run_id),
  });

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId ?? ""),
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? RUN_POLL_MS : false),
  });

  const noFeedYet = feed.data === null;
  const hasFeed = feed.data != null;
  const { mutate: startBuild, isPending: starting, isError: startFailed } = refresh;
  useEffect(() => {
    if (noFeedYet && runId === null && !starting && !startFailed) {
      rebuiltThisLoad.add(profileId);
      startBuild();
    }
  }, [noFeedYet, profileId, runId, starting, startFailed, startBuild]);

  // The saved feed opens instantly; a reload then rebuilds it in the background (a failure, such
  // as the hourly limit, just leaves the saved feed in place).
  useEffect(() => {
    if (hasFeed && runId === null && !starting && !rebuiltThisLoad.has(profileId)) {
      rebuiltThisLoad.add(profileId);
      startBuild();
    }
  }, [hasFeed, profileId, runId, starting, startBuild]);

  const runStatus = run.data?.status;
  useEffect(() => {
    if (runStatus === "done" || runStatus === "failed") {
      void queryClient.invalidateQueries({ queryKey: feedKey(profileId) });
    }
  }, [runStatus, profileId, queryClient]);

  const building = starting || (runId !== null && (run.isPending || runStatus === "running"));

  return {
    feed,
    run: run.data ?? null,
    building,
    buildFailed: runStatus === "failed" || startFailed,
    buildError: refresh.error,
    refresh: () => refresh.mutate(),
  };
}

function mapItems(feed: Feed, update: (item: FeedItem) => FeedItem): Feed {
  return {
    ...feed,
    hero: feed.hero ? update(feed.hero) : null,
    rows: feed.rows.map((row) => ({ ...row, items: row.items.map(update) })),
  };
}

function withoutItem(feed: Feed, ref: string): Feed {
  return {
    ...feed,
    hero: feed.hero?.ref === ref ? null : feed.hero,
    rows: feed.rows
      .map((row) => ({ ...row, items: row.items.filter((item) => item.ref !== ref) }))
      .filter((row) => row.items.length > 0),
  };
}

/** An ask run's extra row lives in its result, so likes and dismissals patch it there too. */
function mapRunItems(
  run: AgentRun | undefined,
  update: (items: FeedItem[]) => FeedItem[],
): AgentRun | undefined {
  const items = run?.result?.items;
  if (!run || !run.result || !Array.isArray(items)) {
    return run;
  }
  return { ...run, result: { ...run.result, items: update(items as FeedItem[]) } };
}

type Toggle = "liked" | "saved";

/**
 * Like, save, open and "not interested", applied to the cached feed at once and sent to the
 * backend. Each change shows a toast with Undo.
 */
export function useItemActions(profileId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const patchFeed = useCallback(
    (change: (feed: Feed) => Feed) => {
      queryClient.setQueryData<Feed | null>(feedKey(profileId), (feed) =>
        feed ? change(feed) : feed,
      );
    },
    [profileId, queryClient],
  );

  const setFlag = useCallback(
    (ref: string, flag: Toggle, value: boolean) => {
      patchFeed((feed) =>
        mapItems(feed, (item) => (item.ref === ref ? { ...item, [flag]: value } : item)),
      );
      queryClient.setQueriesData<FeedItem>({ queryKey: ["item", profileId, ref] }, (item) =>
        item ? { ...item, [flag]: value } : item,
      );
      queryClient.setQueriesData<AgentRun>({ queryKey: ["run"] }, (run) =>
        mapRunItems(run, (items) =>
          items.map((item) => (item.ref === ref ? { ...item, [flag]: value } : item)),
        ),
      );
    },
    [patchFeed, profileId, queryClient],
  );

  const toggle = useCallback(
    (item: FeedItem, flag: Toggle) => {
      async function apply(value: boolean, announce: boolean): Promise<void> {
        setFlag(item.ref, flag, value);
        const signal =
          flag === "liked" ? (value ? "liked" : "unliked") : value ? "saved" : "unsaved";
        try {
          const result = await sendFeedback(profileId, item, signal);
          if (result.stale) {
            patchFeed((feed) => ({ ...feed, stale: true }));
          }
          if (announce && value) {
            const message = flag === "liked" ? `Liked ${item.title}` : `Saved ${item.title}`;
            toast.show(message, () => void apply(false, false));
          }
          void queryClient.invalidateQueries({ queryKey: ["library", profileId] });
        } catch {
          setFlag(item.ref, flag, !value);
          toast.show("That didn't save. Try again?");
        }
      }
      return apply(!item[flag], true);
    },
    [patchFeed, profileId, queryClient, setFlag, toast],
  );

  const notInterested = useCallback(
    async (item: FeedItem) => {
      const before = queryClient.getQueryData<Feed | null>(feedKey(profileId));
      const runsBefore = queryClient.getQueriesData<AgentRun>({ queryKey: ["run"] });
      const restore = () => {
        if (before) {
          queryClient.setQueryData(feedKey(profileId), before);
        }
        for (const [key, run] of runsBefore) {
          queryClient.setQueryData(key, run);
        }
      };
      patchFeed((feed) => ({ ...withoutItem(feed, item.ref), stale: true }));
      queryClient.setQueriesData<AgentRun>({ queryKey: ["run"] }, (run) =>
        mapRunItems(run, (items) => items.filter((known) => known.ref !== item.ref)),
      );
      try {
        await sendFeedback(profileId, item, "not_interested");
        if (item.entity_type === "artist") {
          // Their songs go too, and only the server knows which cards are theirs.
          void queryClient.invalidateQueries({ queryKey: feedKey(profileId) });
        }
        toast.show(`Got it, no more ${item.title}`, () => {
          void (async () => {
            const entries = await listExclusions(profileId);
            const entry = entries.find((exclusion) => exclusion.entity_ref === item.ref);
            if (entry) {
              await removeExclusion(profileId, entry.id);
            }
            restore();
          })();
        });
      } catch {
        restore();
        toast.show("Couldn't hide that one. Try again?");
      }
    },
    [patchFeed, profileId, queryClient, toast],
  );

  const dislike = useCallback(
    async (item: FeedItem): Promise<boolean> => {
      try {
        const result = await sendFeedback(profileId, item, "disliked");
        if (result.stale) {
          patchFeed((feed) => ({ ...feed, stale: true }));
        }
        toast.show(`Noted. Fewer picks like ${item.title}.`);
        return true;
      } catch {
        toast.show("That didn't save. Try again?");
        return false;
      }
    },
    [patchFeed, profileId, toast],
  );

  const opened = useCallback(
    (item: FeedItem, platform: string) => {
      void sendFeedback(profileId, item, "opened", platform).catch(() => undefined);
    },
    [profileId],
  );

  return {
    toggleLike: (item: FeedItem) => toggle(item, "liked"),
    toggleSave: (item: FeedItem) => toggle(item, "saved"),
    notInterested,
    dislike,
    opened,
  };
}
