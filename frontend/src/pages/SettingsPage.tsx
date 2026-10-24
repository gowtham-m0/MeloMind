import { useParams } from "react-router";

import { useProfile } from "@/features/profiles/hooks";
import { DeleteProfile } from "@/features/settings/DeleteProfile";
import { NotInterestedList } from "@/features/settings/NotInterestedList";
import { ProfileForm } from "@/features/settings/ProfileForm";
import { ErrorState, Skeleton } from "@/shared/ui/states";

/** Settings for the profile in the URL: its details, what it hid, and deleting it. */
export function SettingsPage() {
  const { profileId = "" } = useParams();
  const profile = useProfile(profileId);

  if (profile.isPending) {
    return <Skeleton className="h-96 w-full max-w-2xl" />;
  }
  if (profile.isError) {
    return <ErrorState error={profile.error} onRetry={() => void profile.refetch()} />;
  }

  return (
    <div className="flex max-w-2xl flex-col gap-10">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">Settings</h1>
        <p className="mt-1 text-body">For {profile.data.display_name}'s profile only.</p>
      </div>

      <section aria-labelledby="profile-title" className="flex flex-col gap-4">
        <h2 id="profile-title" className="text-[22px] font-semibold">
          Profile
        </h2>
        <ProfileForm key={profile.data.id} profile={profile.data} />
      </section>

      <section aria-labelledby="hidden-title" className="flex flex-col gap-3">
        <div>
          <h2 id="hidden-title" className="text-[22px] font-semibold">
            Not interested
          </h2>
          <p className="mt-1 text-body">
            These never show up in your feed, in any row. Changed your mind? Bring one back.
          </p>
        </div>
        <NotInterestedList profileId={profileId} />
      </section>

      <section aria-labelledby="delete-title" className="flex flex-col gap-3">
        <div>
          <h2 id="delete-title" className="text-[22px] font-semibold">
            Delete profile
          </h2>
          <p className="mt-1 text-body">Your other profiles stay as they are.</p>
        </div>
        <DeleteProfile profile={profile.data} />
      </section>
    </div>
  );
}
