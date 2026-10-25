import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";

import type { Feed } from "@/shared/api/feed";
import { getRun } from "@/shared/api/feed";
import {
  confirmAll,
  createEntry,
  decideLink,
  deleteEntry,
  listEntries,
  suggestLinks,
  type JournalEntry,
  type JournalEntryCreate,
  type JournalLink,
} from "@/shared/api/journal";
import { useToast } from "@/shared/ui/toast";

const RUN_POLL_MS = 1000;

export const journalKey = (profileId: string) => ["journal", profileId] as const;

/** The journal's entries, newest first. */
export function useJournal(profileId: string) {
  return useQuery({ queryKey: journalKey(profileId), queryFn: () => listEntries(profileId) });
}

/**
 * Polls an agent run (a link run here) once a second while it works. When it ends, the journal
 * is fetched again so its suggestions show up.
 */
export function useLinkRun(profileId: string, runId: string | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["run", runId],
    queryFn: async () => {
      const run = await getRun(runId ?? "");
      if (run.status !== "running") {
        await queryClient.invalidateQueries({ queryKey: journalKey(profileId) });
      }
      return run;
    },
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? RUN_POLL_MS : false),
  });
}

function replaceEntry(entries: JournalEntry[] | undefined, entry: JournalEntry): JournalEntry[] {
  const rest = (entries ?? []).filter((known) => known.id !== entry.id);
  return [entry, ...rest].sort((a, b) =>
    a.date === b.date ? b.created_at.localeCompare(a.created_at) : b.date.localeCompare(a.date),
  );
}

/** Saves a new entry; the agent starts suggesting links straight away. */
export function useCreateEntry(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: JournalEntryCreate) => createEntry(profileId, body),
    onSuccess: (entry) => {
      queryClient.setQueryData<JournalEntry[]>(journalKey(profileId), (entries) =>
        replaceEntry(entries, entry),
      );
    },
  });
}

/** Deletes an entry; its links and their signals go too. */
export function useDeleteEntry(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) => deleteEntry(profileId, entryId),
    onSuccess: async (_result, entryId) => {
      queryClient.setQueryData<JournalEntry[]>(journalKey(profileId), (entries) =>
        (entries ?? []).filter((entry) => entry.id !== entryId),
      );
      markFeedStale(queryClient, profileId);
      await queryClient.invalidateQueries({ queryKey: ["taste", profileId] });
    },
  });
}

/** Asks the agent for suggestions again. Returns the entry with its new run. */
export function useSuggestAgain(profileId: string) {
  return useMutation({ mutationFn: (entryId: string) => suggestLinks(profileId, entryId) });
}

function markFeedStale(queryClient: ReturnType<typeof useQueryClient>, profileId: string) {
  queryClient.setQueryData<Feed | null>(["feed", profileId], (feed) =>
    feed ? { ...feed, stale: true } : feed,
  );
}

/**
 * Confirm or reject suggestions, applied to the cached entry at once. A confirmed item moves
 * into the entry's links and shapes the feed; a rejected one is never suggested again.
 */
export function useLinkDecisions(profileId: string) {
  const queryClient = useQueryClient();
  const toast = useToast();

  const patch = useCallback(
    (entryId: string, change: (entry: JournalEntry) => JournalEntry) => {
      queryClient.setQueryData<JournalEntry[]>(journalKey(profileId), (entries) =>
        (entries ?? []).map((entry) => (entry.id === entryId ? change(entry) : entry)),
      );
    },
    [profileId, queryClient],
  );

  const afterConfirm = useCallback(async () => {
    markFeedStale(queryClient, profileId);
    toast.show("Added to your taste. Refresh your feed to see it.");
    await queryClient.invalidateQueries({ queryKey: ["taste", profileId] });
  }, [profileId, queryClient, toast]);

  const decide = useCallback(
    async (entryId: string, link: JournalLink, status: "confirmed" | "rejected") => {
      const before = queryClient.getQueryData<JournalEntry[]>(journalKey(profileId));
      patch(entryId, (entry) => ({
        ...entry,
        suggestions: entry.suggestions.filter((known) => known.id !== link.id),
        links: status === "confirmed" ? [...entry.links, { ...link, status }] : entry.links,
      }));
      try {
        await decideLink(profileId, link.id, status);
        if (status === "confirmed") {
          await afterConfirm();
        }
      } catch {
        queryClient.setQueryData(journalKey(profileId), before);
        toast.show("That didn't save. Try again?");
      }
    },
    [afterConfirm, patch, profileId, queryClient, toast],
  );

  const confirmEvery = useCallback(
    async (entryId: string) => {
      const before = queryClient.getQueryData<JournalEntry[]>(journalKey(profileId));
      patch(entryId, (entry) => ({
        ...entry,
        links: [
          ...entry.links,
          ...entry.suggestions.map((link) => ({ ...link, status: "confirmed" as const })),
        ],
        suggestions: [],
      }));
      try {
        const entry = await confirmAll(profileId, entryId);
        patch(entryId, () => entry);
        await afterConfirm();
      } catch {
        queryClient.setQueryData(journalKey(profileId), before);
        toast.show("That didn't save. Try again?");
      }
    },
    [afterConfirm, patch, profileId, queryClient, toast],
  );

  return { decide, confirmEvery };
}
