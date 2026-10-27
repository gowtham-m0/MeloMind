import { cn } from "cn";
import { AlertTriangle, Check } from "lucide-react";

import type { AgentRun } from "@/shared/api/feed";

const NODE_LABELS: Record<string, string> = {
  load_context: "Reading your taste",
  research: "Agent researching with Qloo",
  fallback: "Filling gaps",
  build_rows: "Building rows",
  add_songs: "Finding songs",
  guardrails: "Checking the rules",
  decorate: "Adding images and links",
  explain: "Summing up",
  feed: "Done",
  extract: "Reading your entry",
  resolve: "Finding it in Qloo",
  match: "Matching things up",
  ask: "Building your row",
  save: "Saving suggestions",
  link: "Linking",
  interpret: "Working out what you meant",
  ladder: "Searching Qloo",
};

/** The agent's plain-English log, step by step, announced as it grows. */
export function AgentLog({
  run,
  compact = false,
  label = "How the agent built this feed",
}: {
  run: AgentRun | null;
  compact?: boolean;
  label?: string;
}) {
  const steps = run?.steps ?? [];
  const shown = compact ? steps.slice(-6) : steps;
  return (
    <ol aria-live="polite" aria-label={label} className="flex flex-col gap-2.5">
      {shown.length === 0 && <li className="text-sm text-muted">Starting the agent…</li>}
      {shown.map((step, index) => (
        <li key={`${step.at}-${index}`} className="rise-in flex gap-3 text-sm">
          <span
            className={cn(
              "mt-0.5 grid size-5 shrink-0 place-items-center rounded-full",
              step.level === "warning"
                ? "bg-primary-tint text-primary-ink"
                : "bg-book/12 text-book-ink",
            )}
          >
            {step.level === "warning" ? (
              <AlertTriangle className="size-3" />
            ) : (
              <Check className="size-3" />
            )}
          </span>
          <span className="min-w-0">
            <span className="block text-xs font-semibold text-muted">
              {NODE_LABELS[step.node] ?? step.node}
            </span>
            <span className="block text-body">{step.message}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}
