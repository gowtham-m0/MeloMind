import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { sessionKeys } from "@/features/sessions/hooks";
import { listExclusions, removeExclusion } from "@/shared/api/exclusions";

/** The profile's rejected and hidden items. */
export function useExclusions(profileId: string) {
  return useQuery({
    queryKey: sessionKeys.exclusions(profileId),
    queryFn: () => listExclusions(profileId),
  });
}

/** Lets an item back in after review. It can then reach the shelf and plans again. */
export function useRemoveExclusion(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (exclusionId: string) => removeExclusion(profileId, exclusionId),
    onSuccess: (remaining) => {
      queryClient.setQueryData(sessionKeys.exclusions(profileId), remaining);
      void queryClient.invalidateQueries({ queryKey: sessionKeys.shelf(profileId) });
    },
  });
}
