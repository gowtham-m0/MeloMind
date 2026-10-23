import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { ProfileEditForm } from "@/features/profiles/ProfileEditForm";
import { ProfileLoader } from "@/features/profiles/ProfileLoader";

/** Edit a profile's details: the same questions as onboarding, on one page. */
export function ProfileEditPage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <ProfileLoader id={id}>
        {(profile) => (
          <section aria-labelledby="edit-title" className="flex max-w-2xl flex-col gap-6">
            <h1 id="edit-title" className="text-3xl font-semibold">
              Edit {profile.display_name}
            </h1>
            <ProfileEditForm profile={profile} />
          </section>
        )}
      </ProfileLoader>
    </RequireSession>
  );
}
