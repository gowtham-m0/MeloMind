import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { Feed } from "@/shared/api/feed";
import {
  addFavourite,
  createProfile,
  deleteProfile,
  getProfile,
  listProfiles,
  updateProfile,
  type FavouriteCreate,
  type ProfileCreate,
  type ProfileUpdate,
} from "@/shared/api/profiles";

/** The signed-in user's profiles. */
export function useProfiles() {
  return useQuery({ queryKey: ["profiles"], queryFn: listProfiles });
}

/** One profile with its favourites. */
export function useProfile(profileId: string) {
  return useQuery({ queryKey: ["profile", profileId], queryFn: () => getProfile(profileId) });
}

/** Creates a profile and refreshes the list. */
export function useCreateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileCreate) => createProfile(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["profiles"] }),
  });
}

/** Saves a favourite, which marks the feed out of date. */
export function useAddFavourite(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: FavouriteCreate) => addFavourite(profileId, body),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
    },
  });
}

const AVATAR_COLOURS = ["bg-music", "bg-film", "bg-tv", "bg-book"];

/** A stable avatar colour per profile, from the four type colours. */
export function avatarColour(profileId: string): string {
  let hash = 0;
  for (const char of profileId) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return AVATAR_COLOURS[hash % AVATAR_COLOURS.length];
}

/** Saves profile fields. Country and birth year change rows, so the feed is marked stale. */
export function useUpdateProfile(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => updateProfile(profileId, body),
    onSuccess: async (profile) => {
      queryClient.setQueryData(["profile", profileId], profile);
      queryClient.setQueryData<Feed | null>(["feed", profileId], (feed) =>
        feed ? { ...feed, stale: true } : feed,
      );
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}

/** Deletes a profile and everything it owns, then forgets its cached data. */
export function useDeleteProfile(profileId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteProfile(profileId),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: ["profile", profileId] });
      queryClient.removeQueries({ queryKey: ["feed", profileId] });
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
    },
  });
}
