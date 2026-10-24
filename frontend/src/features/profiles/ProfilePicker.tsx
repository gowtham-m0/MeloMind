import { cn } from "cn";
import { Plus } from "lucide-react";
import { Link } from "react-router";

import { ErrorState, Skeleton } from "@/shared/ui/states";

import { avatarColour, useProfiles } from "./hooks";

/** Netflix-style profile picker: big avatars, then "Add profile". */
export function ProfilePicker() {
  const profiles = useProfiles();

  if (profiles.isPending) {
    return (
      <div className="grid grid-cols-2 gap-6 sm:grid-cols-3 md:grid-cols-4" aria-busy>
        {[0, 1, 2].map((index) => (
          <Skeleton key={index} className="aspect-square w-full rounded-2xl" />
        ))}
      </div>
    );
  }
  if (profiles.isError) {
    return <ErrorState error={profiles.error} onRetry={() => void profiles.refetch()} />;
  }

  return (
    <ul className="grid grid-cols-2 gap-x-6 gap-y-8 sm:grid-cols-3 md:grid-cols-4">
      {profiles.data.map((profile, index) => (
        <li key={profile.id} className="rise-in" style={{ animationDelay: `${index * 50}ms` }}>
          <Link
            to={`/p/${profile.id}`}
            className="group flex flex-col items-center gap-3 rounded-2xl p-2 text-center"
          >
            <span
              className={cn(
                "lift grid aspect-square w-full place-items-center rounded-2xl font-display text-6xl font-semibold text-ink/85",
                avatarColour(profile.id),
              )}
            >
              {profile.display_name.slice(0, 1).toUpperCase()}
            </span>
            <span className="flex flex-col">
              <span className="text-lg font-semibold text-ink">{profile.display_name}</span>
              <span className="text-sm text-muted">
                {profile.favourites.length} favourite{profile.favourites.length === 1 ? "" : "s"}
                {profile.is_demo ? " · demo" : ""}
              </span>
            </span>
          </Link>
        </li>
      ))}
      <li>
        <Link
          to="/profiles/new"
          className="group flex flex-col items-center gap-3 rounded-2xl p-2 text-center"
        >
          <span className="grid aspect-square w-full place-items-center rounded-2xl border-2 border-dashed border-line text-muted transition-colors group-hover:border-primary group-hover:text-primary-ink">
            <Plus className="size-10" strokeWidth={1.5} />
          </span>
          <span className="text-lg font-semibold text-ink">Add profile</span>
        </Link>
      </li>
    </ul>
  );
}
