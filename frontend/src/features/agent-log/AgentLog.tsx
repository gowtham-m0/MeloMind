import { cn } from "cn";

import { ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useAgentRun } from "./hooks";

// Plain names for the workflow's steps.
const STEP_NAMES: Record<string, string> = {
  load_context: "Getting ready",
  research: "AI research",
  fallback: "Rule-based plan",
  select_items: "Choosing",
  resolve_media: "Finding videos",
  guardrails: "Safety checks",
  compose: "Writing notes",
  plan: "Plan",
};

const STATUS_TEXT = {
  running: "Working…",
  done: "Finished.",
  failed: "Stopped with a problem.",
} as const;

interface AgentLogProps {
  runId: string;
  title?: string;
}

/** The agent's log in plain English, updated once a second and announced to screen readers. */
export function AgentLog({ runId, title = "What the agent is doing" }: AgentLogProps) {
  const run = useAgentRun(runId);

  if (run.isPending) {
    return <LoadingState label="Loading the agent log…" />;
  }
  if (run.isError) {
    return (
      <ErrorBanner
        error={run.error}
        title="Couldn't load the agent log"
        onRetry={() => void run.refetch()}
      />
    );
  }
  const { steps, status } = run.data;
  return (
    <section aria-labelledby={`log-${runId}`} className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id={`log-${runId}`} className="text-2xl font-semibold">
          {title}
        </h2>
        <p className="text-muted-foreground">{STATUS_TEXT[status]}</p>
      </div>
      <ol aria-live="polite" className="flex flex-col gap-2 rounded-lg border-2 bg-card p-4">
        {steps.length === 0 && <li className="text-muted-foreground">Starting…</li>}
        {steps.map((step, index) => (
          <li
            key={`${step.at}-${index}`}
            className={cn(
              "flex flex-col gap-0.5 border-l-4 pl-3 sm:flex-row sm:gap-3",
              step.level === "warning" ? "border-destructive" : "border-primary",
            )}
          >
            <span className="shrink-0 text-base font-bold text-muted-foreground sm:w-40">
              {STEP_NAMES[step.node] ?? step.node}
            </span>
            <span>{step.message}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
