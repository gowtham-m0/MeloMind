import { createContext, useContext } from "react";

import type { AskRequest } from "@/shared/api/ask";
import type { AgentRun, FeedRow } from "@/shared/api/feed";

export interface AskApi {
  /** Starts a run. `label` names it while it works ("Chill picks"). */
  ask: (request: AskRequest, label: string) => void;
  /** True from the tap until the row (or a failure) arrives. */
  running: boolean;
  label: string;
  run: AgentRun | null;
  /** The finished row, until dismissed. */
  row: FeedRow | null;
  dismiss: () => void;
  openComposer: () => void;
}

export const AskContext = createContext<AskApi | null>(null);

/** Reads the ask state. Only valid inside the app shell. */
export function useAsk(): AskApi {
  const api = useContext(AskContext);
  if (!api) {
    throw new Error("useAsk needs an AskProvider");
  }
  return api;
}
