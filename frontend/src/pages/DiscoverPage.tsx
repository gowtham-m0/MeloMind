import { cn } from "cn";
import { NavLink, useParams } from "react-router";

import { CardGrid } from "@/features/feed/CardGrid";
import { useFeedSnapshot } from "@/features/feed/hooks";
import type { FeedItem } from "@/shared/api/feed";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";
import { ITEM_TYPES, TYPE_META, type ItemType } from "@/shared/ui/types";

function isItemType(value: string | undefined): value is ItemType {
  return ITEM_TYPES.includes(value as ItemType);
}

/** Everything in the feed, one type at a time. */
export function DiscoverPage() {
  const { profileId = "", type } = useParams();
  const feed = useFeedSnapshot(profileId);
  const selected = isItemType(type) ? type : null;
  const base = `/p/${profileId}/discover`;

  const items: FeedItem[] = [];
  const seen = new Set<string>();
  for (const item of [feed.data?.hero, ...(feed.data?.rows.flatMap((row) => row.items) ?? [])]) {
    if (item && !seen.has(item.ref) && (!selected || item.entity_type === selected)) {
      seen.add(item.ref);
      items.push(item);
    }
  }

  const tab = (isActive: boolean) =>
    cn(
      "inline-flex h-10 items-center gap-2 rounded-full border px-4 text-sm font-semibold whitespace-nowrap transition-colors",
      isActive
        ? "border-ink bg-ink text-white"
        : "border-line text-body hover:border-[#c9c9c9] hover:text-ink",
    );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">
          {selected ? TYPE_META[selected].plural : "Discover"}
        </h1>
        <p className="mt-1 text-body">Every pick in your feed right now, sorted by type.</p>
      </div>
      <nav aria-label="Types" className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4">
        <NavLink to={base} end className={({ isActive }) => tab(isActive)}>
          All
        </NavLink>
        {ITEM_TYPES.map((itemType) => {
          const meta = TYPE_META[itemType];
          return (
            <NavLink
              key={itemType}
              to={`${base}/${itemType}`}
              className={({ isActive }) => tab(isActive)}
            >
              <span aria-hidden className={cn("size-2 rounded-full", meta.dot)} />
              {meta.plural}
            </NavLink>
          );
        })}
      </nav>
      {feed.isPending ? (
        <Skeleton className="h-80 w-full" />
      ) : feed.isError ? (
        <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />
      ) : items.length === 0 ? (
        <EmptyState title="Nothing here yet">
          Your feed is still building, or it has no picks of this type today. Refresh from Home to
          get more.
        </EmptyState>
      ) : (
        <CardGrid profileId={profileId} items={items} />
      )}
    </div>
  );
}
