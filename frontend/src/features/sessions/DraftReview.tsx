import { Link } from "react-router";

import { formatLength } from "@/features/player/format";
import type { SessionDraft } from "@/shared/api/sessions";
import { Button, buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner } from "@/shared/ui/states";

import { useChangeSession, useEditItems } from "./hooks";
import { ItemCard } from "./ItemCard";
import { PromptEditor } from "./PromptEditor";

interface DraftReviewProps {
  session: SessionDraft;
  firstName: string;
}

/** The caregiver reviews a draft: remove, reorder, reword prompts, then approve. */
export function DraftReview({ session, firstName }: DraftReviewProps) {
  const edit = useEditItems(session.id);
  const change = useChangeSession(session.id);
  const ids = session.items.map((item) => item.id);
  const warmup = session.mode === "warmup";

  const move = (index: number, offset: number) => {
    const order = [...ids];
    const [moved] = order.splice(index, 1);
    order.splice(index + offset, 0, moved);
    edit.mutate({ order });
  };

  return (
    <section aria-labelledby="draft-title" className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 id="draft-title" className="text-3xl font-semibold">
          {warmup ? "Review the warm-up set" : "Review today's session"}
        </h1>
        <p className="text-muted-foreground">
          {session.items.length} items,{" "}
          {warmup
            ? "for the this-or-that warm-up in Person mode."
            : `${formatLength(session.total_duration_s)} in all (aim: ${session.target_minutes} minutes).`}{" "}
          Nothing is played until you approve it.
        </p>
      </div>
      {edit.isError && <ErrorBanner error={edit.error} title="Couldn't change the draft" />}
      {session.items.length === 0 ? (
        <EmptyState title="Every item was removed">
          <Link
            to={`/profiles/${session.profile_id}/plan`}
            className={buttonVariants({ variant: "outline" })}
          >
            Plan again
          </Link>
        </EmptyState>
      ) : (
        <ol className="flex flex-col gap-4">
          {session.items.map((item, index) => (
            <li key={item.id}>
              <ItemCard item={item} firstName={firstName}>
                {!warmup && item.prompt && (
                  <PromptEditor
                    prompt={item.prompt}
                    saving={edit.isPending}
                    onSave={(text) => edit.mutate({ prompts: { [item.id]: text } })}
                  />
                )}
                <div className="flex flex-wrap gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={index === 0 || edit.isPending}
                    onClick={() => move(index, -1)}
                    aria-label={`Move ${item.title} up`}
                  >
                    Move up
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={index === ids.length - 1 || edit.isPending}
                    onClick={() => move(index, 1)}
                    aria-label={`Move ${item.title} down`}
                  >
                    Move down
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={edit.isPending}
                    onClick={() => edit.mutate({ removed: [item.id] })}
                    aria-label={`Remove ${item.title}`}
                  >
                    Remove
                  </Button>
                </div>
              </ItemCard>
            </li>
          ))}
        </ol>
      )}
      {change.isError && <ErrorBanner error={change.error} title="Couldn't approve" />}
      <Button
        size="lg"
        className="self-start"
        disabled={session.items.length === 0 || change.isPending}
        onClick={() => change.mutate("approve")}
      >
        {warmup ? "Approve all" : "Approve this session"}
      </Button>
    </section>
  );
}
