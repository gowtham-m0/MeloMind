import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";

import { askAgent, type AskRequest } from "@/shared/api/ask";
import { getRun, type AgentRun, type FeedRow } from "@/shared/api/feed";
import { useToast } from "@/shared/ui/toast";

import { AskComposer } from "./AskComposer";
import { AskContext, type AskApi } from "./useAsk";

const RUN_POLL_MS = 1000;

function toRow(result: AgentRun["result"]): FeedRow | null {
  if (!result || !Array.isArray(result.items) || result.items.length === 0) {
    return null;
  }
  return {
    key: "ask",
    title: "Picked for you",
    subtitle: "",
    placement: "main",
    ...(result as Partial<FeedRow>),
    items: result.items as FeedRow["items"],
  };
}

/**
 * One extra row the agent builds on request: a mood from "Your vibe today", a surprise, or the
 * user's own words from the top bar. It lives in the shell so the rail and the top bar share it,
 * and the feed shows the row above its others until it's dismissed.
 */
export function AskProvider({ profileId, children }: { profileId: string; children: ReactNode }) {
  const toast = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const [runId, setRunId] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [composerOpen, setComposerOpen] = useState(false);
  const reported = useRef<string | null>(null);

  const start = useMutation({
    mutationFn: (request: AskRequest) => askAgent(profileId, request),
    onSuccess: (started) => setRunId(started.agent_run_id),
    onError: (error) =>
      toast.show(error instanceof Error ? error.message : "Couldn't start that. Try again?"),
  });

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId ?? ""),
    enabled: runId !== null,
    refetchInterval: (query) => (query.state.data?.status === "running" ? RUN_POLL_MS : false),
  });

  const status = run.data?.status;
  useEffect(() => {
    if (runId !== null && status === "failed" && reported.current !== runId) {
      reported.current = runId;
      toast.show("The agent couldn't build that row. Try again?");
    }
  }, [runId, status, toast]);

  const { mutate } = start;
  const home = `/p/${profileId}`;
  const ask = useCallback(
    (request: AskRequest, nextLabel: string) => {
      setLabel(nextLabel);
      setRunId(null);
      setDismissed(null);
      mutate(request);
      if (location.pathname !== home) {
        void navigate(home);
      }
    },
    [home, location.pathname, mutate, navigate],
  );

  const row = useMemo(
    () => (status === "done" && runId !== dismissed ? toRow(run.data?.result ?? null) : null),
    [status, runId, dismissed, run.data?.result],
  );
  const running = start.isPending || (runId !== null && (run.isPending || status === "running"));

  const api: AskApi = {
    ask,
    running,
    label,
    run: run.data ?? null,
    row,
    dismiss: () => setDismissed(runId),
    openComposer: () => setComposerOpen(true),
  };

  return (
    <AskContext.Provider value={api}>
      {children}
      <AskComposer
        open={composerOpen}
        onOpenChange={setComposerOpen}
        busy={running}
        onSubmit={(text) => {
          setComposerOpen(false);
          ask({ text }, "Your request");
        }}
      />
    </AskContext.Provider>
  );
}
