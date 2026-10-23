import type { Favourite } from "@/shared/api/profiles";
import { Button } from "@/shared/ui/button";
import { EmptyState, ErrorBanner } from "@/shared/ui/states";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

import { useRemoveFavourite } from "./hooks";

interface FavouriteListProps {
  profileId: string;
  favourites: Favourite[];
}

/** A profile's favourites, each with whether it was matched in Qloo, and a way to remove it. */
export function FavouriteList({ profileId, favourites }: FavouriteListProps) {
  const remove = useRemoveFavourite(profileId);

  if (favourites.length === 0) {
    return (
      <EmptyState title="No favourites yet">
        <p>Add a singer, song, film, TV show or book they loved when they were young.</p>
      </EmptyState>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {remove.isError && (
        <ErrorBanner error={remove.error} title="Couldn't remove that favourite" />
      )}
      <ul className="flex flex-col gap-3">
        {favourites.map((favourite) => (
          <li
            key={favourite.id}
            className="flex flex-wrap items-center gap-3 rounded-lg border-2 bg-card p-4"
          >
            <TypeIcon type={favourite.kind} className="size-6 text-primary" />
            <div className="flex min-w-0 flex-1 flex-col">
              <span className="font-bold">
                {favourite.song_title ? `“${favourite.song_title}”` : favourite.name}
              </span>
              <span className="text-base text-muted-foreground">
                {ITEM_TYPE_LABELS[favourite.kind]}
                {favourite.song_title ? ` · ${favourite.name}` : ""}
                {favourite.verified ? " · Matched" : " · Saved as text"}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              disabled={remove.isPending && remove.variables === favourite.id}
              onClick={() => remove.mutate(favourite.id)}
              aria-label={`Remove ${favourite.song_title ?? favourite.name}`}
            >
              Remove
            </Button>
          </li>
        ))}
      </ul>
    </div>
  );
}
