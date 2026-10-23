import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  changeSession,
  editItems,
  getHistory,
  getSession,
  planSession,
  reactToItem,
  type ItemsPatch,
  type PlanRequest,
  type Reaction,
  type SessionAction,
  type SessionDraft,
} from "@/shared/api/sessions";

const POLL_MS = 1000;

/** Query keys for sessions, history and the shelf they feed. */
export const sessionKeys = {
  detail: (id: string) => ["sessions", id] as const,
  history: (profileId: string) => ["history", profileId] as const,
  shelf: (profileId: string) => ["shelf", profileId] as const,
  exclusions: (profileId: string) => ["exclusions", profileId] as const,
};

/** One session, polled once a second while the agent is still planning it. */
export function useSessionDraft(id: string | undefined) {
  return useQuery({
    queryKey: sessionKeys.detail(id ?? ""),
    queryFn: () => getSession(id ?? ""),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === "planning" ? POLL_MS : false),
  });
}

/** A profile's sessions and warm-up sets, newest first. */
export function useHistory(profileId: string | undefined) {
  return useQuery({
    queryKey: sessionKeys.history(profileId ?? ""),
    queryFn: () => getHistory(profileId ?? ""),
    enabled: Boolean(profileId),
  });
}

function useStoreSession() {
  const queryClient = useQueryClient();
  return (session: SessionDraft) => {
    queryClient.setQueryData(sessionKeys.detail(session.id), session);
    void queryClient.invalidateQueries({ queryKey: sessionKeys.history(session.profile_id) });
    void queryClient.invalidateQueries({ queryKey: sessionKeys.shelf(session.profile_id) });
  };
}

/** Starts planning a session or a warm-up set. */
export function usePlanSession(profileId: string) {
  const store = useStoreSession();
  return useMutation({
    mutationFn: (body: PlanRequest) => planSession(profileId, body),
    onSuccess: store,
  });
}

/** Removes, reorders or re-prompts a draft's items. */
export function useEditItems(sessionId: string) {
  const store = useStoreSession();
  return useMutation({
    mutationFn: (patch: ItemsPatch) => editItems(sessionId, patch),
    onSuccess: store,
  });
}

/** Approves, starts or completes a session. */
export function useChangeSession(sessionId: string) {
  const store = useStoreSession();
  return useMutation({
    mutationFn: (action: SessionAction) => changeSession(sessionId, action),
    onSuccess: store,
  });
}

/** The caregiver's reaction to an item. Rejecting or hiding changes the shelf. */
export function useReactToItem(session: SessionDraft) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ itemId, reaction }: { itemId: string; reaction: Reaction }) =>
      reactToItem(session.id, itemId, reaction),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: sessionKeys.shelf(session.profile_id) });
      void queryClient.invalidateQueries({
        queryKey: sessionKeys.exclusions(session.profile_id),
      });
    },
  });
}
