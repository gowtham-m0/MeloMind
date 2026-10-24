import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";

import { CardGrid } from "@/features/feed/CardGrid";
import { getLibrary } from "@/shared/api/feed";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";

/** Saved and liked items. The not-interested list lives in Settings. */
export function SavedPage() {
  const { profileId = "" } = useParams();
  const library = useQuery({
    queryKey: ["library", profileId],
    queryFn: () => getLibrary(profileId),
  });

  if (library.isPending) {
    return <Skeleton className="h-96 w-full" />;
  }
  if (library.isError) {
    return <ErrorState error={library.error} onRetry={() => void library.refetch()} />;
  }

  return (
    <div className="flex flex-col gap-10">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">Saved</h1>
        <p className="mt-1 text-body">What you've bookmarked and loved. Likes steer your feed.</p>
      </div>

      <section aria-labelledby="saved-title" className="flex flex-col gap-4">
        <h2 id="saved-title" className="text-[22px] font-semibold">
          For later
        </h2>
        {library.data.saved.length === 0 ? (
          <EmptyState title="Nothing saved yet">
            Tap the bookmark on any card to keep it here.
          </EmptyState>
        ) : (
          <CardGrid profileId={profileId} items={library.data.saved} />
        )}
      </section>

      <section aria-labelledby="liked-title" className="flex flex-col gap-4">
        <h2 id="liked-title" className="text-[22px] font-semibold">
          Liked
        </h2>
        {library.data.liked.length === 0 ? (
          <EmptyState title="No likes yet">
            Heart a few picks and refresh: the agent follows.
          </EmptyState>
        ) : (
          <CardGrid profileId={profileId} items={library.data.liked} />
        )}
      </section>

      <p className="text-sm text-muted">
        Looking for things you marked “Not interested”? They're in{" "}
        <Link
          to={`/p/${profileId}/settings`}
          className="font-semibold text-primary-ink hover:underline"
        >
          Settings
        </Link>
        .
      </p>
    </div>
  );
}
