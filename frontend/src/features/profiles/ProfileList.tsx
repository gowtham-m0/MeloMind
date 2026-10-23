import { Link } from "react-router";

import { countryName } from "@/shared/data/countries";
import { buttonVariants } from "@/shared/ui/button";
import { EmptyState, ErrorBanner, LoadingState } from "@/shared/ui/states";

import { useProfiles } from "./hooks";
import { describeProfile } from "./describe";

/** The caregiver's profiles as large, tappable cards. */
export function ProfileList() {
  const profiles = useProfiles();

  if (profiles.isPending) {
    return <LoadingState label="Loading profiles…" />;
  }
  if (profiles.isError) {
    return (
      <ErrorBanner
        error={profiles.error}
        title="Couldn't load profiles"
        onRetry={() => void profiles.refetch()}
      />
    );
  }
  if (profiles.data.length === 0) {
    return (
      <EmptyState title="No profiles yet">
        <p>A name and a birth year are enough to start.</p>
        <Link to="/profiles/new" className={buttonVariants()}>
          Add a profile
        </Link>
      </EmptyState>
    );
  }

  return (
    <ul className="grid gap-4 sm:grid-cols-2">
      {profiles.data.map((profile) => (
        <li key={profile.id}>
          <Link
            to={`/profiles/${profile.id}`}
            className="flex min-h-28 flex-col gap-1 rounded-lg border-2 bg-card p-5 hover:bg-accent"
          >
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-serif text-2xl font-semibold">{profile.display_name}</span>
              {profile.is_demo && (
                <span className="rounded-full border border-destructive px-2 text-base font-bold text-destructive">
                  Sample
                </span>
              )}
            </span>
            <span className="text-muted-foreground">
              {describeProfile(
                profile.birth_year,
                profile.places_lived,
                countryName(profile.country_code),
              )}
            </span>
            <span className="text-muted-foreground">
              {profile.favourites.length === 1
                ? "1 favourite"
                : `${profile.favourites.length} favourites`}
            </span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
