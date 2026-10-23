import { Link } from "react-router";

import { RequireSession } from "@/features/demo/RequireSession";
import { ProfileList } from "@/features/profiles/ProfileList";
import { buttonVariants } from "@/shared/ui/button";

/** The caregiver's profiles. */
export function ProfilesPage() {
  return (
    <RequireSession>
      <section aria-labelledby="profiles-title" className="flex flex-col gap-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 id="profiles-title" className="text-3xl font-semibold">
            Profiles
          </h1>
          <Link to="/profiles/new" className={buttonVariants()}>
            Add a profile
          </Link>
        </div>
        <ProfileList />
      </section>
    </RequireSession>
  );
}
