import { OnboardingFlow } from "@/features/onboarding/OnboardingFlow";
import { RequireSession } from "@/features/session/RequireSession";

/** A new profile: name, country, favourites and the taste quiz, then the first feed builds. */
export function NewProfilePage() {
  return (
    <RequireSession>
      <OnboardingFlow />
    </RequireSession>
  );
}
