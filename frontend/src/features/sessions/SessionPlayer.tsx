import { Link, useSearchParams } from "react-router";

import { useProfile } from "@/features/profiles/hooks";
import { ApiError } from "@/shared/api/client";
import type { SessionDraft } from "@/shared/api/sessions";
import { Button, buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useChangeSession, useReactToItem, useSessionDraft } from "./hooks";
import { ItemPlayer } from "./ItemPlayer";
import { SessionComplete } from "./SessionComplete";

/**
 * The caregiver's player for an approved session. The item number is in the URL, so a
 * refresh carries on where it was.
 */
export function SessionPlayer({ sessionId }: { sessionId: string | undefined }) {
  const session = useSessionDraft(sessionId);
  const profile = useProfile(session.data?.profile_id);

  if (session.isPending || (session.isSuccess && profile.isPending)) {
    return <LoadingState label="Loading the session…" />;
  }
  if (session.isError) {
    if (session.error instanceof ApiError && session.error.status === 404) {
      return (
        <EmptyState title="We couldn't find that session">
          <Link to="/profiles" className={buttonVariants({ variant: "outline" })}>
            Back to profiles
          </Link>
        </EmptyState>
      );
    }
    return (
      <ErrorBanner
        error={session.error}
        title="Couldn't load the session"
        onRetry={() => void session.refetch()}
      />
    );
  }
  const firstName = profile.data?.display_name.split(" ")[0] ?? "They";
  return <PlayerForStatus session={session.data} firstName={firstName} />;
}

function PlayerForStatus({ session, firstName }: { session: SessionDraft; firstName: string }) {
  const change = useChangeSession(session.id);

  if (session.status === "completed") {
    return <SessionComplete profileId={session.profile_id} firstName={firstName} />;
  }
  if (session.status === "approved" && session.mode !== "warmup") {
    return (
      <section aria-labelledby="start-title" className="flex flex-col gap-4">
        <h1 id="start-title" className="text-3xl font-semibold">
          Ready when you are
        </h1>
        <p className="max-w-prose">
          Sit together, and press Play on each item when you're both ready. Nothing starts on its
          own, and Stop is always at the bottom of the screen.
        </p>
        {change.isError && <ErrorBanner error={change.error} title="Couldn't start" />}
        <Button
          size="lg"
          className="self-start"
          disabled={change.isPending}
          onClick={() => change.mutate("start")}
        >
          Start the session
        </Button>
      </section>
    );
  }
  if (session.status !== "in_progress") {
    return (
      <EmptyState title="This session isn't ready to play">
        <Link to={`/sessions/${session.id}`} className={buttonVariants({ variant: "outline" })}>
          Go to the session
        </Link>
      </EmptyState>
    );
  }
  return <PlayingSession session={session} firstName={firstName} />;
}

function PlayingSession({ session, firstName }: { session: SessionDraft; firstName: string }) {
  const [params, setParams] = useSearchParams();
  const change = useChangeSession(session.id);
  const react = useReactToItem(session);
  const count = session.items.length;
  const index = Math.min(Math.max(Number(params.get("item") ?? 0) || 0, 0), count - 1);
  const item = session.items[index];
  const goTo = (next: number) => setParams({ item: String(next) }, { replace: true });

  return (
    <section aria-labelledby="player-title" className="flex flex-col gap-5">
      <div className="flex flex-col gap-2">
        <h1 id="player-title" className="text-lg font-semibold text-muted-foreground">
          Item {index + 1} of {count}
        </h1>
        <div
          role="progressbar"
          aria-label="Session progress"
          aria-valuemin={1}
          aria-valuemax={count}
          aria-valuenow={index + 1}
          className="h-3 overflow-hidden rounded-full bg-secondary"
        >
          <div className="h-full bg-primary" style={{ width: `${((index + 1) / count) * 100}%` }} />
        </div>
      </div>
      {change.isError && <ErrorBanner error={change.error} title="Couldn't finish the session" />}
      <ItemPlayer
        key={item.id}
        item={item}
        firstName={firstName}
        onReact={(reaction) => react.mutateAsync({ itemId: item.id, reaction })}
        navigation={
          <>
            <Button
              size="lg"
              variant="outline"
              disabled={index === 0}
              onClick={() => goTo(index - 1)}
            >
              Previous
            </Button>
            {index < count - 1 ? (
              <Button size="lg" variant="secondary" onClick={() => goTo(index + 1)}>
                Next item
              </Button>
            ) : (
              <Button
                size="lg"
                variant="secondary"
                disabled={change.isPending}
                onClick={() => change.mutate("complete")}
              >
                Finish
              </Button>
            )}
          </>
        }
      />
    </section>
  );
}
