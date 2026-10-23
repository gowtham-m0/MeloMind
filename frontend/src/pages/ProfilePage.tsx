import { useParams } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { FavouriteList } from "@/features/favourites/FavouriteList";
import { FavouritesEditor } from "@/features/favourites/FavouritesEditor";
import { ProfileDetails } from "@/features/profiles/ProfileDetails";
import { ProfileLoader } from "@/features/profiles/ProfileLoader";

/** One profile: details and favourites. Sessions and memories arrive in later phases. */
export function ProfilePage() {
  const { id } = useParams();

  return (
    <RequireSession>
      <ProfileLoader id={id}>
        {(profile) => (
          <div className="flex flex-col gap-10">
            <ProfileDetails profile={profile} />
            <section aria-labelledby="favourites-title" className="flex flex-col gap-4">
              <h2 id="favourites-title" className="text-2xl font-semibold">
                Favourites
              </h2>
              <FavouriteList profileId={profile.id} favourites={profile.favourites} />
            </section>
            <FavouritesEditor profileId={profile.id} />
          </div>
        )}
      </ProfileLoader>
    </RequireSession>
  );
}
