import { Link } from "react-router";

import type { Profile } from "@/shared/api/profiles";
import { countryName } from "@/shared/data/countries";
import { buttonVariants } from "@/shared/ui/button";

import { describeProfile } from "./describe";

/** A profile's name and the basics the agent starts from, with a link to edit them. */
export function ProfileDetails({ profile }: { profile: Profile }) {
  return (
    <section aria-labelledby="profile-name" className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <h1 id="profile-name" className="text-4xl font-semibold">
          {profile.display_name}
        </h1>
        {profile.is_demo && (
          <span className="rounded-full border-2 border-destructive px-3 text-base font-bold text-destructive">
            Sample profile
          </span>
        )}
      </div>
      <p className="text-muted-foreground">
        {describeProfile(
          profile.birth_year,
          profile.places_lived,
          countryName(profile.country_code),
        )}
      </p>
      {profile.languages.length > 0 && (
        <p className="text-muted-foreground">Languages: {profile.languages.join(", ")}</p>
      )}
      <Link
        to={`/profiles/${profile.id}/edit`}
        className={buttonVariants({ variant: "outline", className: "self-start" })}
      >
        Edit details
      </Link>
    </section>
  );
}
