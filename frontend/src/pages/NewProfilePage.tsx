import { RequireSession } from "@/features/demo/RequireSession";
import { OnboardingStepper } from "@/features/onboarding/OnboardingStepper";

/** Onboarding: a new profile from a name and a birth year, then optional questions. */
export function NewProfilePage() {
  return (
    <RequireSession>
      <OnboardingStepper />
    </RequireSession>
  );
}
