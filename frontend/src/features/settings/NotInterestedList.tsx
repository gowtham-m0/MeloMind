import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RotateCcw } from "lucide-react";

import { listExclusions, removeExclusion } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { TypeChip } from "@/shared/ui/chip";
import { ErrorState, Skeleton } from "@/shared/ui/states";
import { useToast } from "@/shared/ui/toast";
import type { ItemType } from "@/shared/ui/types";

import { feedKey } from "../feed/hooks";

const dateFormat = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short" });

/** Everything marked "not interested", newest first, each with a way to bring it back (rule 3). */
export function NotInterestedList({ profileId }: { profileId: string }) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const exclusions = useQuery({
    queryKey: ["exclusions", profileId],
    queryFn: () => listExclusions(profileId),
  });
  const undo = useMutation({
    mutationFn: (exclusionId: string) => removeExclusion(profileId, exclusionId),
    onSuccess: async (remaining, exclusionId) => {
      const title = exclusions.data?.find((entry) => entry.id === exclusionId)?.title;
      queryClient.setQueryData(["exclusions", profileId], remaining);
      await queryClient.invalidateQueries({ queryKey: feedKey(profileId) });
      toast.show(title ? `${title} can show up again.` : "It can show up again.");
    },
  });

  if (exclusions.isPending) {
    return <Skeleton className="h-32 w-full" />;
  }
  if (exclusions.isError) {
    return <ErrorState error={exclusions.error} onRetry={() => void exclusions.refetch()} />;
  }
  if (exclusions.data.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-line bg-surface-2/60 p-4 text-body">
        Nothing hidden. Mark a card “Not interested” and it never shows up again, until you bring it
        back here.
      </p>
    );
  }

  return (
    <ul className="flex flex-col divide-y divide-line rounded-xl border border-line">
      {exclusions.data.map((entry) => (
        <li key={entry.id} className="flex items-center justify-between gap-3 px-4 py-3">
          <span className="flex min-w-0 flex-col gap-0.5">
            <span className="truncate font-semibold text-ink">{entry.title}</span>
            <span className="flex items-center gap-2">
              {entry.entity_type && <TypeChip type={entry.entity_type as ItemType} />}
              <span className="text-xs text-muted">
                Hidden {dateFormat.format(new Date(entry.created_at))}
              </span>
            </span>
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => undo.mutate(entry.id)}
            disabled={undo.isPending}
            aria-label={`Bring back ${entry.title}`}
          >
            <RotateCcw /> Bring back
          </Button>
        </li>
      ))}
    </ul>
  );
}
