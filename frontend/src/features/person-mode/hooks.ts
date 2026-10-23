import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { sessionKeys } from "@/features/sessions/hooks";
import {
  getShelf,
  nextWarmupPair,
  reactToCard,
  sendPersonSignal,
  type PersonSignal,
} from "@/shared/api/person";
import type { Reaction } from "@/shared/api/sessions";

/** The Person-mode shelf: approved, playable cards only. */
export function useShelf(profileId: string) {
  return useQuery({ queryKey: sessionKeys.shelf(profileId), queryFn: () => getShelf(profileId) });
}

/** The first warm-up pair. Choosing nothing records nothing, so it's safe to fetch again. */
export function useFirstWarmupPair(profileId: string) {
  return useQuery({
    queryKey: ["warmup-first", profileId],
    queryFn: () => nextWarmupPair(profileId, null, []),
    staleTime: Infinity,
    gcTime: 0,
    retry: false,
  });
}

/** Records a warm-up choice and fetches the next pair. */
export function useNextWarmupPair(profileId: string) {
  return useMutation({
    mutationFn: ({ chosenRef, shownRefs }: { chosenRef: string; shownRefs: string[] }) =>
      nextWarmupPair(profileId, chosenRef, shownRefs),
  });
}

/** A tap in Person mode: chose, loved, replayed or skipped. */
export function usePersonSignal(profileId: string) {
  return useMutation({
    mutationFn: ({
      itemRef,
      signal,
      playedS,
    }: {
      itemRef: string;
      signal: PersonSignal;
      playedS?: number;
    }) => sendPersonSignal(profileId, itemRef, signal, playedS),
  });
}

/** The caregiver's reaction from inside Person mode. Hiding or rejecting changes the shelf. */
export function useReactToCard(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemRef, reaction }: { itemRef: string; reaction: Reaction }) =>
      reactToCard(profileId, itemRef, reaction),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.shelf(profileId) });
      void queryClient.invalidateQueries({ queryKey: sessionKeys.exclusions(profileId) });
    },
  });
}
