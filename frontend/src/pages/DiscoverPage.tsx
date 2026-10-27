import { cn } from "cn";
import { Search, X } from "lucide-react";
import { useState } from "react";
import { NavLink, useParams, useSearchParams } from "react-router";

import { CardGrid } from "@/features/feed/CardGrid";
import { useFeedSnapshot } from "@/features/feed/hooks";
import type { FeedItem } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { SourceBadge } from "@/shared/ui/chip";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

interface Group {
  /** The URL segment: `/discover/<key>`. */
  key: ItemType;
  title: string;
  blurb: string;
  /** Everything the group shows, with a label for the narrower filter inside it. */
  kinds: { type: ItemType; label: string }[];
}

const GROUPS: Group[] = [
  {
    key: "artist",
    title: "Music",
    blurb: "Artists Qloo matched to your taste, and their best-known songs.",
    kinds: [
      { type: "artist", label: "Artists" },
      { type: "song", label: "Songs" },
    ],
  },
  {
    key: "movie",
    title: "Movies & TV",
    blurb: "Films and shows to queue up next.",
    kinds: [
      { type: "movie", label: "Films" },
      { type: "tv_show", label: "TV shows" },
    ],
  },
  {
    key: "book",
    title: "Books",
    blurb: "Reads that fit the way you feel about everything else.",
    kinds: [{ type: "book", label: "Books" }],
  },
];

/** Old links named one type; each one still lands in its group, narrowed to that type. */
const LEGACY: Partial<Record<ItemType, { group: ItemType; only: ItemType }>> = {
  tv_show: { group: "movie", only: "tv_show" },
  song: { group: "artist", only: "song" },
};

function matches(item: FeedItem, query: string): boolean {
  const haystack = [item.title, item.creator, item.reason, ...item.tags]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return query
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .every((word) => haystack.includes(word));
}

const pill = (isActive: boolean) =>
  cn(
    "inline-flex h-11 items-center gap-2 rounded-full border px-4 text-sm font-semibold whitespace-nowrap transition-colors",
    isActive
      ? "border-ink bg-ink text-white"
      : "border-line text-body hover:border-[#c9c9c9] hover:text-ink",
  );

/** Everything in the feed: by type, narrowed by kind (artists, songs, films, shows) and by a
 * word or two typed into the filter. */
export function DiscoverPage() {
  const { profileId = "", type } = useParams();
  const [params, setParams] = useSearchParams();
  const feed = useFeedSnapshot(profileId);
  const [filter, setFilter] = useState("");
  const base = `/p/${profileId}/discover`;

  const legacy = LEGACY[type as ItemType];
  const group = GROUPS.find((candidate) => candidate.key === (legacy?.group ?? type)) ?? null;
  const requestedOnly = legacy?.only ?? params.get("only");
  const only = group?.kinds.find((kind) => kind.type === requestedOnly)?.type ?? null;

  const all: FeedItem[] = [];
  const seen = new Set<string>();
  for (const item of [feed.data?.hero, ...(feed.data?.rows.flatMap((row) => row.items) ?? [])]) {
    if (item && !seen.has(item.ref)) {
      seen.add(item.ref);
      all.push(item);
    }
  }

  const inGroup = group
    ? all.filter((item) => group.kinds.some((kind) => kind.type === item.entity_type))
    : all;
  const shown = (only ? inGroup.filter((item) => item.entity_type === only) : inGroup).filter(
    (item) => matches(item, filter),
  );
  const countOf = (kindType: ItemType) =>
    inGroup.filter((item) => item.entity_type === kindType).length;

  const chooseOnly = (next: ItemType | null) =>
    setParams(next ? { only: next } : {}, { replace: true });

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[34px] leading-tight font-semibold">{group?.title ?? "Discover"}</h1>
        <p className="mt-1 text-body">
          {group?.blurb ?? "Every pick in your feed right now, sorted by type."}
        </p>
      </div>

      <nav aria-label="Types" className="no-scrollbar -mx-4 flex gap-2 overflow-x-auto px-4">
        <NavLink to={base} end className={({ isActive }) => pill(isActive)}>
          All
        </NavLink>
        {GROUPS.map((candidate) => {
          const meta = TYPE_META[candidate.key];
          return (
            <NavLink
              key={candidate.key}
              to={`${base}/${candidate.key}`}
              className={() => pill(group?.key === candidate.key)}
            >
              <span aria-hidden className={cn("size-2 rounded-full", meta.dot)} />
              {candidate.title}
            </NavLink>
          );
        })}
      </nav>

      <div className="flex flex-wrap items-center gap-3">
        {group && group.kinds.length > 1 && (
          <div
            role="group"
            aria-label="Narrow down"
            className="flex rounded-full bg-surface-2 p-1 text-sm font-semibold"
          >
            {[{ type: null, label: "Both" }, ...group.kinds].map((kind) => {
              const active = only === kind.type;
              const count = kind.type ? countOf(kind.type) : inGroup.length;
              return (
                <button
                  key={kind.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => chooseOnly(kind.type)}
                  className={cn(
                    "flex h-9 items-center gap-1.5 rounded-full px-3.5 transition-colors pointer-coarse:h-11",
                    active ? "bg-surface text-ink shadow-soft" : "text-muted hover:text-ink",
                  )}
                >
                  {kind.label} <span className="tabular text-xs font-medium">{count}</span>
                </button>
              );
            })}
          </div>
        )}
        <label className="relative flex min-w-[220px] flex-1 items-center sm:max-w-sm">
          <span className="sr-only">Filter these picks by title, tag or reason</span>
          <Search className="pointer-events-none absolute left-3.5 size-4 text-muted" aria-hidden />
          <input
            type="search"
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            placeholder="Filter by title, tag or reason"
            className="h-11 w-full rounded-full border border-transparent bg-surface-2 pr-11 pl-10 text-base text-ink placeholder:text-muted focus:border-primary focus:bg-surface"
          />
          {filter && (
            <button
              type="button"
              onClick={() => setFilter("")}
              aria-label="Clear filter"
              className="absolute right-1 grid size-9 place-items-center rounded-full text-muted hover:bg-surface-3"
            >
              <X className="size-4" />
            </button>
          )}
        </label>
        {!feed.isPending && !feed.isError && (
          <p aria-live="polite" className="tabular text-sm text-muted">
            {shown.length} {shown.length === 1 ? "pick" : "picks"}
          </p>
        )}
        {all[0] && <SourceBadge source={all[0].source} />}
      </div>

      {feed.isPending ? (
        <Skeleton className="h-80 w-full" />
      ) : feed.isError ? (
        <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />
      ) : shown.length === 0 ? (
        filter ? (
          <EmptyState
            title={`Nothing matches “${filter.trim()}”`}
            action={
              <Button variant="secondary" onClick={() => setFilter("")}>
                Clear the filter
              </Button>
            }
          >
            Try a tag like “indie”, or a title or an artist's name.
          </EmptyState>
        ) : (
          <EmptyState title="Nothing here yet">
            Your feed is still building, or it has no picks of this kind today. Refresh from Home to
            get more.
          </EmptyState>
        )
      ) : (
        <CardGrid profileId={profileId} items={shown} />
      )}
    </div>
  );
}
