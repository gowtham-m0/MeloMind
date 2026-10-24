import { ArrowRight } from "lucide-react";
import { Link } from "react-router";

import type { Feed, FeedItem } from "@/shared/api/feed";
import { Thumb } from "@/shared/ui/thumb";
import { type ItemType } from "@/shared/ui/types";

interface Tile {
  type: ItemType;
  title: string;
  blurb: string;
  matches: ItemType[];
}

const TILES: Tile[] = [
  { type: "artist", title: "Music", blurb: "Artists on your wavelength", matches: ["artist"] },
  {
    type: "movie",
    title: "Movies & TV",
    blurb: "Films and shows to queue up",
    matches: ["movie", "tv_show"],
  },
  { type: "book", title: "Books", blurb: "Your next late-night read", matches: ["book"] },
];

function firstImageOf(feed: Feed, types: ItemType[]): FeedItem | undefined {
  const items = feed.rows.flatMap((row) => row.items);
  return (
    items.find((item) => types.includes(item.entity_type as ItemType) && item.image_url) ??
    items.find((item) => types.includes(item.entity_type as ItemType))
  );
}

/** Music, Movies & TV and Books, each wearing the image of its top pick in your feed. */
export function CategoryTiles({ feed, profileId }: { feed: Feed; profileId: string }) {
  return (
    <nav aria-label="Browse by type" className="grid grid-cols-3 gap-3 md:gap-4">
      {TILES.map((tile) => {
        const cover = firstImageOf(feed, tile.matches);
        return (
          <Link
            key={tile.type}
            to={`/p/${profileId}/discover/${tile.type}`}
            className="lift group relative isolate overflow-hidden rounded-xl"
          >
            <Thumb
              src={cover?.image_url}
              title={tile.title}
              type={tile.type}
              aspect="wide"
              className="aspect-[4/3] rounded-xl sm:aspect-[16/10]"
            />
            <div
              aria-hidden
              className="absolute inset-0 rounded-xl bg-[linear-gradient(0deg,#1a1a1ae6_0%,#1a1a1a66_45%,#1a1a1a00_75%)]"
            />
            <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 p-3 md:p-4">
              <span className="min-w-0">
                <span className="block font-display text-[15px] leading-tight font-semibold text-balance text-white md:text-xl">
                  {tile.title}
                </span>
                <span className="hidden text-[13px] text-white/75 md:block">{tile.blurb}</span>
              </span>
              <span className="hidden size-9 shrink-0 place-items-center rounded-full bg-white/20 text-white backdrop-blur transition-transform duration-200 group-hover:translate-x-0.5 sm:grid">
                <ArrowRight className="size-4" />
              </span>
            </div>
          </Link>
        );
      })}
    </nav>
  );
}
