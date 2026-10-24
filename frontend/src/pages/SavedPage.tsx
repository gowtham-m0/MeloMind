import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";
import { useParams } from "react-router";

import { CardGrid } from "@/features/feed/CardGrid";
import { feedKey } from "@/features/feed/hooks";
import { getLibrary, listExclusions, removeExclusion } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { TypeChip } from "@/shared/ui/chip";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";
import type { ItemType } from "@/shared/ui/types";

/** Saved and liked items, and the not-interested list with undo. */
export function SavedPage() {
  const { profileId = "" } = useParams();
  const queryClient = useQueryClient();
  const library = useQuery({
    queryKey: ["library", profileId],
    queryFn: () => getLibrary(profileId),
  });
  const exclusions = useQuery({
    queryKey: ["exclusions", profileId],
    queryFn: () => listExclusions(profileId),
  });
  const undo = useMutation({
    mutationFn: (exclusionId: string) => removeExclusion(profileId, exclusionId),
    onSuccess: async (remaining) => {
      queryClient.setQueryData(["exclusions", profileId], remaining);
      await queryClient.invalidateQueries({ queryKey: feedKey(profileId) });
    },
  });

  if (library.isPending) {
    return <Skeleton className="h-96 w-full" />;
  }
  if (library.isError) {
    return <ErrorState error={library.error} onRetry={() => void library.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">Saved</h1>
        <p className="mt-1 text-body">What you've bookmarked and loved. Likes steer your feed.</p>
      </div>

      <section aria-labelledby="saved-title" className="flex flex-col gap-4">
        <h2 id="saved-title" className="text-[22px] font-semibold">
          For later
        </h2>
        {library.data.saved.length === 0 ? (
          <EmptyState title="Nothing saved yet">
            Tap the bookmark on any card to keep it here.
          </EmptyState>
        ) : (
          <CardGrid profileId={profileId} items={library.data.saved} />
        )}
      </section>

      <section aria-labelledby="liked-title" className="flex flex-col gap-4">
        <h2 id="liked-title" className="text-[22px] font-semibold">
          Liked
        </h2>
        {library.data.liked.length === 0 ? (
          <EmptyState title="No likes yet">
            Heart a few picks and refresh: the agent follows.
          </EmptyState>
        ) : (
          <CardGrid profileId={profileId} items={library.data.liked} />
        )}
      </section>

      <section aria-labelledby="hidden-title" className="flex flex-col gap-3">
        <h2 id="hidden-title" className="text-[22px] font-semibold">
          Not interested
        </h2>
        <p className="text-body">
          These never show up in your feed. Changed your mind? Bring one back.
        </p>
        {exclusions.data && exclusions.data.length > 0 ? (
          <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
            {exclusions.data.map((entry) => (
              <li key={entry.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-semibold text-ink">{entry.title}</span>
                  {entry.entity_type && <TypeChip type={entry.entity_type as ItemType} />}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => undo.mutate(entry.id)}
                  disabled={undo.isPending}
                >
                  <RotateCcw /> Bring back
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted">Nothing hidden.</p>
        )}
      </section>
    </div>
  );
}
