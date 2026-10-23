import type { Session } from "@supabase/supabase-js";
import { useEffect, useState } from "react";

import { supabase } from "@/shared/api/supabase";

interface SessionState {
  session: Session | null;
  isLoading: boolean;
}

/** The current Supabase session, kept up to date as the user signs in or out. */
export function useSession(): SessionState {
  const [state, setState] = useState<SessionState>({ session: null, isLoading: supabase !== null });

  useEffect(() => {
    if (!supabase) {
      return;
    }
    let active = true;
    void supabase.auth.getSession().then(({ data }) => {
      if (active) {
        setState({ session: data.session, isLoading: false });
      }
    });
    const { data } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({ session, isLoading: false });
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
    };
  }, []);

  return state;
}
