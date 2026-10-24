import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { seedDemo } from "@/shared/api/demo";
import { supabase } from "@/shared/api/supabase";

/** Signs in anonymously unless a session already exists. */
export async function ensureSignedIn(): Promise<void> {
  if (!supabase) {
    throw new Error(
      "Sign-in isn't set up. Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to .env.local.",
    );
  }
  const { data } = await supabase.auth.getSession();
  if (!data.session) {
    const { error } = await supabase.auth.signInAnonymously();
    if (error) {
      throw new Error(`Couldn't sign you in: ${error.message}`);
    }
  }
}

/** Signs in, creates the sample profiles once (their feeds start building), then opens the
 * profile picker. */
export function useTryDemo() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async () => {
      await ensureSignedIn();
      return seedDemo();
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
      await navigate("/profiles");
    },
  });
}

/** Signs out and clears everything cached for the old user. */
export function useSignOut() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async () => {
      await supabase?.auth.signOut();
    },
    onSuccess: async () => {
      queryClient.clear();
      await navigate("/");
    },
  });
}
