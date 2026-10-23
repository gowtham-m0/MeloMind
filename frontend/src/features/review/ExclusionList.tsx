import { Button } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useExclusions, useRemoveExclusion } from "./hooks";

/**
 * Items kept out of sessions and Person mode. Hidden items (they upset the person) wait here
 * for review; the caregiver decides whether to let them back in. A rejection is for good.
 */
export function ExclusionList({ profileId }: { profileId: string }) {
  const exclusions = useExclusions(profileId);
  const remove = useRemoveExclusion(profileId);

  if (exclusions.isPending) {
    return <LoadingState label="Loading hidden and rejected items…" />;
  }
  if (exclusions.isError) {
    return (
      <ErrorBanner
        error={exclusions.error}
        title="Couldn't load the list"
        onRetry={() => void exclusions.refetch()}
      />
    );
  }
  if (exclusions.data.length === 0) {
    return (
      <EmptyState title="Nothing is hidden or rejected">
        <p>Items marked “Upset” or “Reject” during a session appear here.</p>
      </EmptyState>
    );
  }
  return (
    <div className="flex flex-col gap-3">
      {remove.isError && <ErrorBanner error={remove.error} title="Couldn't let it back in" />}
      <ul className="flex flex-col gap-3">
        {exclusions.data.map((entry) => (
          <li
            key={entry.id}
            className="flex flex-wrap items-center justify-between gap-3 rounded-lg border-2 bg-card p-4"
          >
            <div className="flex flex-col">
              <span className="font-bold">{entry.title}</span>
              <span className="text-base text-muted-foreground">
                {entry.reason === "upset"
                  ? entry.needs_review
                    ? "Hidden because it upset them · waiting for your review"
                    : "Hidden because it upset them"
                  : "Rejected: never suggested again"}
              </span>
            </div>
            {entry.reason === "upset" && (
              <Button
                variant="outline"
                size="sm"
                disabled={remove.isPending}
                onClick={() => remove.mutate(entry.id)}
                aria-label={`Let ${entry.title} back in`}
              >
                Let it back in
              </Button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
