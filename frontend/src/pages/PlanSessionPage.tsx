import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { ProfileLoader } from "@/features/profiles/ProfileLoader";
import { PlanForm } from "@/features/sessions/PlanForm";

/** Plan a session with the agent. Its log shows on the session page while it works. */
export function PlanSessionPage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <ProfileLoader id={id}>
        {(profile) => (
          <section aria-labelledby="plan-title" className="flex flex-col gap-6">
            <h1 id="plan-title" className="text-3xl font-semibold">
              Plan a session for {profile.display_name}
            </h1>
            <PlanForm profileId={profile.id} firstName={profile.display_name.split(" ")[0]} />
          </section>
        )}
      </ProfileLoader>
    </RequireSession>
  );
}
