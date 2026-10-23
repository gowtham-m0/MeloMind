import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { profileKeys } from "@/features/profiles/hooks";
import {
  addFavourite,
  removeFavourite,
  type FavouriteCreate,
  type FavouriteKind,
} from "@/shared/api/profiles";
import { searchTaste } from "@/shared/api/taste";

/** The shortest query worth sending to taste search. */
export const MIN_QUERY_LENGTH = 2;

/** Taste-search matches for a (debounced) query and favourite kind. */
export function useTasteSearch(query: string, kind: FavouriteKind, enabled: boolean) {
  return useQuery({
    queryKey: ["taste-search", kind, query],
    queryFn: () => searchTaste(query, kind),
    enabled: enabled && query.length >= MIN_QUERY_LENGTH,
    staleTime: 5 * 60 * 1000,
  });
}

function useRefreshProfile(profileId: string) {
  const queryClient = useQueryClient();
  return async () => {
    await queryClient.invalidateQueries({ queryKey: profileKeys.detail(profileId) });
    await queryClient.invalidateQueries({ queryKey: profileKeys.all, exact: true });
  };
}

/** Saves a favourite on a profile. */
export function useAddFavourite(profileId: string) {
  const refresh = useRefreshProfile(profileId);
  return useMutation({
    mutationFn: (body: FavouriteCreate) => addFavourite(profileId, body),
    onSuccess: refresh,
  });
}

/** Removes a favourite from a profile. */
export function useRemoveFavourite(profileId: string) {
  const refresh = useRefreshProfile(profileId);
  return useMutation({
    mutationFn: (favouriteId: string) => removeFavourite(profileId, favouriteId),
    onSuccess: refresh,
  });
}
