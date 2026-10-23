import { Link, useNavigate } from "react-router";

import { AgentLog } from "@/features/agent-log/AgentLog";
import { useProfile } from "@/features/profiles/hooks";
import { ApiError } from "@/shared/api/client";
import type { SessionDraft } from "@/shared/api/sessions";
import { Button, buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { DraftReview } from "./DraftReview";
import { useChangeSession, useSessionDraft } from "./hooks";
import { SessionComplete } from "./SessionComplete";

/**
 * A session page that follows its status: the agent log while planning, the review while it's
 * a draft, then start, play and completion. Everything comes from the server, so it survives a
 * refresh.
 */
export function SessionView({ sessionId }: { sessionId: string | undefined }) {
  const session = useSessionDraft(sessionId);
  const profile = useProfile(session.data?.profile_id);

  if (session.isPending || (session.isSuccess && profile.isPending)) {
    return <LoadingState label="Loading the session…" />;
  }
  if (session.isError) {
    if (session.error instanceof ApiError && session.error.status === 404) {
      return (
        <EmptyState title="We couldn't find that session">
          <p>It may belong to someone else, or its profile was deleted.</p>
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
  return <ViewForStatus session={session.data} firstName={firstName} />;
}

function ViewForStatus({ session, firstName }: { session: SessionDraft; firstName: string }) {
  const runId = session.agent_run_id;
  const log = runId ? <AgentLog runId={runId} /> : null;
  const plan = `/profiles/${session.profile_id}/plan`;

  switch (session.status) {
    case "planning":
      return (
        <div className="flex flex-col gap-6">
          <h1 className="text-3xl font-semibold">Planning for {firstName}…</h1>
          <p className="text-muted-foreground">This takes up to half a minute.</p>
          {log}
        </div>
      );
    case "failed":
      return (
        <div className="flex flex-col gap-6">
          <EmptyState title="The agent couldn't plan this session">
            <p>The log below says why. You can try again.</p>
            <Link to={plan} className={buttonVariants({ variant: "outline" })}>
              Try again
            </Link>
          </EmptyState>
          {log}
        </div>
      );
    case "draft":
      return (
        <div className="flex flex-col gap-10">
          <DraftReview session={session} firstName={firstName} />
          {runId && (
            <details className="rounded-lg border-2 p-4">
              <summary className="min-h-11 cursor-pointer text-xl font-semibold">
                How the agent chose these
              </summary>
              <div className="mt-4">
                <AgentLog runId={runId} title="The agent's log" />
              </div>
            </details>
          )}
        </div>
      );
    case "completed":
      return <SessionComplete profileId={session.profile_id} firstName={firstName} />;
    default:
      return <Approved session={session} firstName={firstName} />;
  }
}

function Approved({ session, firstName }: { session: SessionDraft; firstName: string }) {
  const change = useChangeSession(session.id);
  const navigate = useNavigate();

  if (session.mode === "warmup") {
    return (
      <EmptyState title="The warm-up set is approved">
        <p>Open Person mode and hand over when {firstName} is ready.</p>
        <Link
          to={`/profiles/${session.profile_id}/person`}
          className={buttonVariants({ size: "lg" })}
        >
          Open Person mode
        </Link>
      </EmptyState>
    );
  }
  if (session.status === "in_progress") {
    return (
      <EmptyState title="This session is in progress">
        <Link to={`/sessions/${session.id}/play`} className={buttonVariants({ size: "lg" })}>
          Carry on playing
        </Link>
      </EmptyState>
    );
  }
  return (
    <section aria-labelledby="approved-title" className="flex flex-col gap-4">
      <h1 id="approved-title" className="text-3xl font-semibold">
        Approved
      </h1>
      <p className="max-w-prose">
        {session.items.length} items are ready. The ones with a video are now on {firstName}'s
        Person-mode shelf too.
      </p>
      {change.isError && <ErrorBanner error={change.error} title="Couldn't start" />}
      <Button
        size="lg"
        className="self-start"
        disabled={change.isPending}
        onClick={() =>
          change.mutate("start", { onSuccess: () => void navigate(`/sessions/${session.id}/play`) })
        }
      >
        Start the session
      </Button>
    </section>
  );
}
