import { useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "cn";
import { List, Network, X } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router";

import { CardGrid } from "@/features/feed/CardGrid";
import { RememberBox } from "@/features/favourites/RememberBox";
import { useItemParam } from "@/features/item-detail/useItemParam";
import { opensDetail } from "@/features/taste/nodes";
import { TasteMapView } from "@/features/taste/TasteMapView";
import { addFavourite, removeFavourite, type Favourite } from "@/shared/api/profiles";
import { getTaste, getTasteMap, type Taste, type TasteMapNode } from "@/shared/api/taste";
import { TagChip, TypeChip } from "@/shared/ui/chip";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";
import { Thumb } from "@/shared/ui/thumb";
import { useToast } from "@/shared/ui/toast";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

const BAR_TYPES: ItemType[] = ["artist", "song", "movie", "tv_show", "book"];

function TypeBar({ counts }: { counts: Record<string, number> }) {
  const total = BAR_TYPES.reduce((sum, type) => sum + (counts[type] ?? 0), 0);
  if (total === 0) {
    return null;
  }
  return (
    <div>
      <div
        className="flex h-3 w-full overflow-hidden rounded-full bg-surface-2"
        role="img"
        aria-label={BAR_TYPES.filter((type) => counts[type])
          .map((type) => `${counts[type]} ${TYPE_META[type].plural.toLowerCase()}`)
          .join(", ")}
      >
        {BAR_TYPES.map((type) =>
          counts[type] ? (
            <span
              key={type}
              className={cn("h-full", TYPE_META[type].dot)}
              style={{ width: `${(counts[type] / total) * 100}%` }}
            />
          ) : null,
        )}
      </div>
      <ul className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-body">
        {BAR_TYPES.filter((type) => counts[type]).map((type) => (
          <li key={type} className="flex items-center gap-1.5">
            <span aria-hidden className={cn("size-2 rounded-full", TYPE_META[type].dot)} />
            <span className="tabular font-semibold text-ink">{counts[type]}</span>{" "}
            {TYPE_META[type].plural}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FavouriteTile({ favourite, onRemove }: { favourite: Favourite; onRemove: () => void }) {
  const type = (favourite.kind === "song" ? "artist" : favourite.kind) as ItemType;
  const { open } = useItemParam();
  const title = favourite.song_title ? `${favourite.song_title}` : favourite.name;
  return (
    <div className="group relative">
      <button
        type="button"
        disabled={!favourite.qloo_id}
        onClick={() => favourite.qloo_id && open(favourite.qloo_id)}
        className="flex w-full flex-col gap-2 text-left"
      >
        <Thumb
          src={favourite.image_url}
          title={favourite.name}
          type={type}
          aspect={type === "artist" ? "square" : "poster"}
          round={type === "artist"}
        />
        <span className="flex flex-col gap-0.5 px-0.5">
          <TypeChip type={favourite.kind === "song" ? "song" : type} />
          <span className="line-clamp-2 text-[15px] leading-snug font-semibold text-ink">
            {title}
          </span>
          {favourite.song_title && <span className="text-xs text-muted">{favourite.name}</span>}
          {!favourite.verified && <span className="text-xs text-muted">Kept as text</span>}
        </span>
      </button>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${title} from your favourites`}
        className="absolute top-2 right-2 grid size-9 place-items-center rounded-full bg-white/90 text-ink shadow-soft transition-opacity duration-200 hover:bg-white md:opacity-0 md:group-focus-within:opacity-100 md:group-hover:opacity-100"
      >
        <X className="size-4" />
      </button>
    </div>
  );
}

function MapList({ nodes, onOpen }: { nodes: TasteMapNode[]; onOpen: (n: TasteMapNode) => void }) {
  const items = nodes.filter((node) => node.kind !== "entry");
  return (
    <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((node) => {
        const type = (node.kind === "place" ? null : node.kind) as ItemType | null;
        const body = (
          <>
            {type ? (
              <Thumb
                src={node.image_url}
                title={node.title}
                type={type}
                aspect="square"
                round
                className="size-10 shrink-0"
              />
            ) : (
              <span className="grid size-10 shrink-0 place-items-center rounded-full bg-surface-3 text-xs font-semibold text-muted">
                Place
              </span>
            )}
            <span className="min-w-0">
              {type && <TypeChip type={type} />}
              <span className="block truncate font-semibold text-ink">{node.title}</span>
            </span>
          </>
        );
        return (
          <li key={node.id}>
            {opensDetail(node) ? (
              <button
                type="button"
                onClick={() => onOpen(node)}
                className="flex w-full items-center gap-3 rounded-xl border border-hairline bg-surface p-2 text-left transition-colors hover:bg-surface-2"
              >
                {body}
              </button>
            ) : (
              <div className="flex items-center gap-3 rounded-xl border border-hairline bg-surface p-2">
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}

/** What MeloMind has learned: your taste in a sentence, top tags, your favourites and likes,
 * and the taste map of how they connect. */
export function TastePage() {
  const { profileId = "" } = useParams();
  const queryClient = useQueryClient();
  const toast = useToast();
  const { open } = useItemParam();
  const [view, setView] = useState<"map" | "list">(() =>
    window.matchMedia("(min-width: 768px)").matches ? "map" : "list",
  );
  const taste = useQuery({ queryKey: ["taste", profileId], queryFn: () => getTaste(profileId) });
  const tasteMap = useQuery({
    queryKey: ["taste", profileId, "map"],
    queryFn: () => getTasteMap(profileId),
  });

  async function refreshTaste() {
    await queryClient.invalidateQueries({ queryKey: ["taste", profileId] });
    await queryClient.invalidateQueries({ queryKey: ["profile", profileId] });
  }

  async function remove(favourite: Favourite) {
    queryClient.setQueryData<Taste>(["taste", profileId], (current) =>
      current
        ? { ...current, favourites: current.favourites.filter((f) => f.id !== favourite.id) }
        : current,
    );
    try {
      await removeFavourite(profileId, favourite.id);
      toast.show(`Removed ${favourite.song_title ?? favourite.name}`, () => {
        void addFavourite(profileId, {
          name: favourite.name,
          kind: favourite.kind,
          entity_id: favourite.qloo_id,
          song_title: favourite.song_title,
          image_url: favourite.image_url,
        }).then(refreshTaste);
      });
    } catch {
      toast.show("Couldn't remove that. Try again?");
    }
    await refreshTaste();
  }

  const openNode = (node: TasteMapNode) => opensDetail(node) && open(node.id);

  if (taste.isPending) {
    return (
      <div className="flex flex-col gap-6">
        <Skeleton className="h-24 w-full max-w-3xl" />
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (taste.isError) {
    return <ErrorState error={taste.error} onRetry={() => void taste.refetch()} />;
  }
  const data = taste.data;
  const topWeight = Math.max(...data.top_tags.map((tag) => tag.weight), 1);

  return (
    <div className="flex flex-col gap-10">
      <header className="flex flex-col gap-5">
        <h1 className="max-w-[24ch] text-[34px] leading-[1.1] font-semibold md:text-[48px]">
          {data.sentence}
        </h1>
        {data.top_tags.length > 0 && (
          <ul aria-label="Top tags" className="flex flex-wrap gap-2">
            {data.top_tags.map((tag) => (
              <li key={tag.name}>
                <TagChip
                  className={cn(
                    tag.weight / topWeight > 0.66 && "border-primary bg-primary-tint text-ink",
                  )}
                  style={{ fontSize: `${13 + Math.round((tag.weight / topWeight) * 4)}px` }}
                >
                  {tag.name}
                </TagChip>
              </li>
            ))}
          </ul>
        )}
        <div className="max-w-xl">
          <TypeBar counts={data.by_type} />
        </div>
      </header>

      <section aria-labelledby="map-title" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="map-title" className="text-[22px] font-semibold">
              Your taste map
            </h2>
            <p className="text-sm text-muted">
              Favourites, likes and what you've written about, and how they connect.
            </p>
          </div>
          <div role="group" aria-label="Show as" className="flex rounded-full bg-surface-2 p-1">
            {(["map", "list"] as const).map((option) => (
              <button
                key={option}
                type="button"
                aria-pressed={view === option}
                onClick={() => setView(option)}
                className={cn(
                  "flex h-9 items-center gap-1.5 rounded-full px-3.5 text-sm font-semibold transition-colors",
                  view === option ? "bg-surface text-ink shadow-soft" : "text-muted",
                )}
              >
                {option === "map" ? <Network className="size-4" /> : <List className="size-4" />}
                {option === "map" ? "Map" : "List"}
              </button>
            ))}
          </div>
        </div>
        {tasteMap.isPending ? (
          <Skeleton className="h-[420px] w-full" />
        ) : tasteMap.isError ? (
          <ErrorState error={tasteMap.error} onRetry={() => void tasteMap.refetch()} />
        ) : tasteMap.data.nodes.length === 0 ? (
          <EmptyState title="Your map grows as you go">
            Like a few things on your feed, or confirm what the agent finds in your journal, and
            they'll show up here.
          </EmptyState>
        ) : view === "map" ? (
          <TasteMapView map={tasteMap.data} onOpen={openNode} />
        ) : (
          <MapList nodes={tasteMap.data.nodes} onOpen={openNode} />
        )}
      </section>

      <section aria-labelledby="favourites-title" className="flex flex-col gap-4">
        <h2 id="favourites-title" className="text-[22px] font-semibold">
          Your favourites
        </h2>
        <RememberBox profileId={profileId} onAdded={() => void refreshTaste()} />
        {data.favourites.length === 0 ? (
          <EmptyState title="No favourites yet">
            Search above, or type a line you remember.
          </EmptyState>
        ) : (
          <ul className="grid grid-cols-2 gap-x-3.5 gap-y-6 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6">
            {data.favourites.map((favourite) => (
              <li key={favourite.id}>
                <FavouriteTile favourite={favourite} onRemove={() => void remove(favourite)} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="likes-title" className="flex flex-col gap-4">
        <h2 id="likes-title" className="text-[22px] font-semibold">
          Recently liked
        </h2>
        {data.recent_likes.length === 0 ? (
          <EmptyState title="No likes yet">
            Heart a few picks on your feed and they'll gather here.
          </EmptyState>
        ) : (
          <CardGrid profileId={profileId} items={data.recent_likes} />
        )}
      </section>
    </div>
  );
}
