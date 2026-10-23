import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { ProfileLoader } from "@/features/profiles/ProfileLoader";
import { ExclusionList } from "@/features/review/ExclusionList";

/** Items waiting for the caregiver's review: what was hidden or rejected. */
export function ReviewPage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <ProfileLoader id={id}>
        {(profile) => (
          <section aria-labelledby="review-title" className="flex flex-col gap-6">
            <h1 id="review-title" className="text-3xl font-semibold">
              Hidden and rejected items for {profile.display_name}
            </h1>
            <p className="max-w-prose text-muted-foreground">
              None of these appear in sessions or in Person mode.
            </p>
            <ExclusionList profileId={profile.id} />
          </section>
        )}
      </ProfileLoader>
    </RequireSession>
  );
}
