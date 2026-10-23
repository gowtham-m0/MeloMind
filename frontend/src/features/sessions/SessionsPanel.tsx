import { Link } from "react-router";

import { formatLength } from "@/features/player/format";
import { buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useHistory } from "./hooks";
import { STATUS_LABELS, modeLabel } from "./labels";

const DATE = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

/** The profile's sessions: plan a new one, open Person mode, and see earlier ones. */
export function SessionsPanel({ profileId }: { profileId: string }) {
  const history = useHistory(profileId);

  return (
    <section aria-labelledby="sessions-title" className="flex flex-col gap-4">
      <h2 id="sessions-title" className="text-2xl font-semibold">
        Sessions
      </h2>
      <div className="flex flex-wrap gap-3">
        <Link to={`/profiles/${profileId}/plan`} className={buttonVariants({ size: "lg" })}>
          Plan a session
        </Link>
        <Link
          to={`/profiles/${profileId}/person`}
          className={buttonVariants({ variant: "outline", size: "lg" })}
        >
          Open Person mode
        </Link>
        <Link
          to={`/profiles/${profileId}/review`}
          className={buttonVariants({ variant: "ghost", size: "lg" })}
        >
          Hidden and rejected items
        </Link>
      </div>
      {history.isPending && <LoadingState label="Loading sessions…" />}
      {history.isError && (
        <ErrorBanner
          error={history.error}
          title="Couldn't load sessions"
          onRetry={() => void history.refetch()}
        />
      )}
      {history.isSuccess && history.data.length === 0 && (
        <EmptyState title="No sessions yet">
          <p>Plan the first one: the agent starts from the details and favourites above.</p>
        </EmptyState>
      )}
      {history.isSuccess && history.data.length > 0 && (
        <ul className="flex flex-col gap-2">
          {history.data.map((entry) => (
            <li key={entry.id}>
              <Link
                to={`/sessions/${entry.id}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded-lg border-2 bg-card p-4 hover:bg-accent"
              >
                <span className="font-bold">
                  {modeLabel(entry.mode)} · {DATE.format(new Date(entry.created_at))}
                </span>
                <span className="text-base text-muted-foreground">
                  {STATUS_LABELS[entry.status]}
                  {entry.item_count > 0 &&
                    ` · ${entry.item_count} items · ${formatLength(entry.total_duration_s)}`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
