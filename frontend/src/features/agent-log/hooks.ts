import { useQuery } from "@tanstack/react-query";

import { getAgentRun } from "@/shared/api/sessions";

const POLL_MS = 1000;

/** Query keys for agent runs. */
export const agentRunKeys = {
  detail: (id: string) => ["agent-runs", id] as const,
};

/** One agent run, polled once a second until it's done or failed. */
export function useAgentRun(id: string | null | undefined) {
  return useQuery({
    queryKey: agentRunKeys.detail(id ?? ""),
    queryFn: () => getAgentRun(id ?? ""),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      if (query.state.status === "error") {
        return false;
      }
      const status = query.state.data?.status;
      return status === undefined || status === "running" ? POLL_MS : false;
    },
  });
}
