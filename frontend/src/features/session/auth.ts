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

/** `signin` replaces the current session; `save` upgrades a guest session, keeping its profiles. */
export type AuthIntent = "signin" | "save";

const NOT_SET_UP =
  "Sign-in isn't set up. Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to .env.local.";

/** Where Google and the email link send the browser back to. */
function returnUrl(): string {
  return `${window.location.origin}/profiles`;
}

/** Turns a Supabase error into a sentence that says what to do next. */
function friendlyAuthError(message: string, intent: AuthIntent): string {
  if (/already (been )?(linked|registered|exists)|already in use/i.test(message)) {
    return intent === "save"
      ? "That account already exists. Sign in with it instead."
      : "That account is already registered. Try the other sign-in option.";
  }
  if (/rate limit|too many/i.test(message)) {
    return "Too many tries. Wait a minute and try again.";
  }
  if (/provider is not enabled|unsupported provider/i.test(message)) {
    return "Google sign-in isn't turned on for this project yet. Use email instead.";
  }
  return `Couldn't sign you in: ${message}`;
}

/** Goes to Google and back. Leaves the page, so it resolves only when something went wrong. */
export async function continueWithGoogle(intent: AuthIntent): Promise<void> {
  if (!supabase) {
    throw new Error(NOT_SET_UP);
  }
  const options = { redirectTo: returnUrl() };
  const { error } =
    intent === "save"
      ? await supabase.auth.linkIdentity({ provider: "google", options })
      : await supabase.auth.signInWithOAuth({ provider: "google", options });
  if (error) {
    throw new Error(friendlyAuthError(error.message, intent));
  }
}

/** Emails a sign-in link (`signin`) or a link that confirms and attaches the address (`save`). */
export async function continueWithEmail(intent: AuthIntent, email: string): Promise<void> {
  if (!supabase) {
    throw new Error(NOT_SET_UP);
  }
  const { error } =
    intent === "save"
      ? await supabase.auth.updateUser({ email }, { emailRedirectTo: returnUrl() })
      : await supabase.auth.signInWithOtp({ email, options: { emailRedirectTo: returnUrl() } });
  if (error) {
    throw new Error(friendlyAuthError(error.message, intent));
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
