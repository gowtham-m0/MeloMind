import { useSession } from "./useSession";

interface Account {
  isLoading: boolean;
  /** Signed in at all, as a guest or with an account. */
  isSignedIn: boolean;
  /** A guest session from "Try the demo": its profiles live only in this browser. */
  isGuest: boolean;
  email: string | null;
}

/** Who is signed in, and whether they're a guest or have a real account. */
export function useAccount(): Account {
  const { session, isLoading } = useSession();
  const user = session?.user ?? null;
  return {
    isLoading,
    isSignedIn: user !== null,
    isGuest: user?.is_anonymous === true,
    email: user?.email ?? null,
  };
}
