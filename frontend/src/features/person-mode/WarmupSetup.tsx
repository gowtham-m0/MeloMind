import {
  useChangeSession,
  useEditItems,
  useHistory,
  usePlanSession,
  useSessionDraft,
} from "@/features/sessions/hooks";
import type { SessionDraft } from "@/shared/api/sessions";
import { Button } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

interface WarmupSetupProps {
  profileId: string;
  onHandOver: () => void;
  onSkip: () => void;
}

/**
 * The caregiver's step before handing over: approve the warm-up set ("Approve all", or remove
 * items first), then start the warm-up or go straight to the shelf.
 */
export function WarmupSetup({ profileId, onHandOver, onSkip }: WarmupSetupProps) {
  const history = useHistory(profileId);
  const latest = history.data?.find((entry) => entry.mode === "warmup");
  const warmup = useSessionDraft(latest?.id);
  const plan = usePlanSession(profileId);

  if (history.isPending || (latest && warmup.isPending)) {
    return <LoadingState label="Checking the warm-up set…" />;
  }
  if (history.isError || warmup.isError) {
    const error = history.error ?? warmup.error;
    return error ? <ErrorBanner error={error} title="Couldn't load the warm-up set" /> : null;
  }

  const prepare = () =>
    plan.mutate(
      { mode: "warmup", target_minutes: 20 },
      { onSuccess: () => void history.refetch() },
    );

  return (
    <section
      aria-labelledby="setup-title"
      className="flex w-full max-w-3xl flex-col gap-6 self-start text-lg"
    >
      <div className="flex flex-col gap-2">
        <h1 id="setup-title" className="text-3xl font-semibold">
          Before you hand over
        </h1>
        <p className="text-muted-foreground">This screen is for you, the caregiver.</p>
      </div>
      {plan.isError && <ErrorBanner error={plan.error} title="Couldn't prepare the warm-up" />}
      {!latest || warmup.data?.status === "failed" ? (
        <EmptyState title="There's no warm-up set yet">
          <p>
            The agent picks about 12 well-known items from their youth for a this-or-that warm-up.
          </p>
          <div className="flex flex-wrap gap-3">
            <Button disabled={plan.isPending} onClick={prepare}>
              Prepare a warm-up set
            </Button>
            <Button variant="outline" onClick={onSkip}>
              Go straight to the shelf
            </Button>
          </div>
        </EmptyState>
      ) : (
        warmup.data && (
          <WarmupSetForReview session={warmup.data} onHandOver={onHandOver} onSkip={onSkip} />
        )
      )}
    </section>
  );
}

interface WarmupSetProps {
  session: SessionDraft;
  onHandOver: () => void;
  onSkip: () => void;
}

function WarmupSetForReview({ session, onHandOver, onSkip }: WarmupSetProps) {
  const edit = useEditItems(session.id);
  const change = useChangeSession(session.id);

  if (session.status === "planning") {
    return (
      <div className="flex flex-col gap-4">
        <LoadingState label="The agent is preparing the warm-up set…" />
        <Button variant="outline" size="lg" className="self-start" onClick={onSkip}>
          Go straight to the shelf
        </Button>
      </div>
    );
  }
  const approved = session.status !== "draft";
  return (
    <div className="flex flex-col gap-4">
      <p>
        {approved
          ? "The warm-up set is approved. Hand over when they're ready."
          : "Check the warm-up set. Remove anything that shouldn't come up, then approve."}
      </p>
      {edit.isError && <ErrorBanner error={edit.error} title="Couldn't remove that item" />}
      {change.isError && <ErrorBanner error={change.error} title="Couldn't approve" />}
      <ul className="flex flex-col gap-2">
        {session.items.map((item) => (
          <li key={item.id} className="flex items-center gap-3 rounded-lg border-2 bg-card p-3">
            <TypeIcon type={item.entity_type} className="size-6 text-primary" />
            <span className="flex-1">
              <span className="font-bold">{item.title}</span>
              <span className="text-muted-foreground">
                {" "}
                · {ITEM_TYPE_LABELS[item.entity_type]}
                {item.release_year != null && ` · ${item.release_year}`}
              </span>
            </span>
            {!approved && (
              <Button
                variant="outline"
                size="sm"
                disabled={edit.isPending}
                onClick={() => edit.mutate({ removed: [item.id] })}
                aria-label={`Remove ${item.title}`}
              >
                Remove
              </Button>
            )}
          </li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-3">
        {approved ? (
          <Button size="lg" onClick={onHandOver}>
            Hand over: start the warm-up
          </Button>
        ) : (
          <Button
            size="lg"
            disabled={change.isPending || session.items.length < 2}
            onClick={() => change.mutate("approve")}
          >
            Approve all
          </Button>
        )}
        <Button variant="outline" size="lg" onClick={onSkip}>
          Go straight to the shelf
        </Button>
      </div>
    </div>
  );
}
