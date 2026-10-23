import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router";

import { seedDemo } from "@/shared/api/demo";
import { supabase } from "@/shared/api/supabase";

/** Signs in anonymously (if needed), creates the sample profiles once, then opens the list. */
export function useTryDemo() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  return useMutation({
    mutationFn: async () => {
      if (!supabase) {
        throw new Error(
          "Sign-in isn't set up. Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to .env.",
        );
      }
      const { data } = await supabase.auth.getSession();
      if (!data.session) {
        const { error } = await supabase.auth.signInAnonymously();
        if (error) {
          throw new Error(`Couldn't start the demo: ${error.message}`);
        }
      }
      return seedDemo();
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["profiles"] });
      await navigate("/profiles");
    },
  });
}
