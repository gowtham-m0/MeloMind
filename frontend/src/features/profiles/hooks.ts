import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createProfile,
  deleteProfile,
  getProfile,
  listProfiles,
  updateProfile,
  type Profile,
  type ProfileCreate,
  type ProfileUpdate,
} from "@/shared/api/profiles";

/** Query keys for profiles, shared with the favourites feature. */
export const profileKeys = {
  all: ["profiles"] as const,
  detail: (id: string) => ["profiles", id] as const,
};

/** The signed-in user's profiles. */
export function useProfiles() {
  return useQuery({ queryKey: profileKeys.all, queryFn: listProfiles });
}

/** One profile with its favourites. */
export function useProfile(id: string | undefined) {
  return useQuery({
    queryKey: profileKeys.detail(id ?? ""),
    queryFn: () => getProfile(id ?? ""),
    enabled: Boolean(id),
  });
}

function useStoreProfile() {
  const queryClient = useQueryClient();
  return (profile: Profile) => {
    queryClient.setQueryData(profileKeys.detail(profile.id), profile);
    void queryClient.invalidateQueries({ queryKey: profileKeys.all, exact: true });
  };
}

/** Creates a profile from a name and birth year (plus anything else known). */
export function useCreateProfile() {
  const store = useStoreProfile();
  return useMutation({
    mutationFn: (body: ProfileCreate) => createProfile(body),
    onSuccess: store,
  });
}

/** Changes some fields of a profile. */
export function useUpdateProfile(id: string) {
  const store = useStoreProfile();
  return useMutation({
    mutationFn: (body: ProfileUpdate) => updateProfile(id, body),
    onSuccess: store,
  });
}

/** Deletes a profile and everything that belongs to it. */
export function useDeleteProfile(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => deleteProfile(id),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: profileKeys.detail(id) });
      await queryClient.invalidateQueries({ queryKey: profileKeys.all, exact: true });
    },
  });
}
