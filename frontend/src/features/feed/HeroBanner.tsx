import { ArrowUpRight, Heart, Info } from "lucide-react";
import { cn } from "cn";

import type { FeedItem } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

interface HeroBannerProps {
  item: FeedItem;
  onWhy: (item: FeedItem) => void;
  onLike: (item: FeedItem) => void;
  onOpened: (item: FeedItem, platform: string) => void;
}

const VERB_PHRASE: Record<ItemType, string> = {
  artist: "Listen to",
  movie: "Watch",
  tv_show: "Binge",
  book: "Read",
  song: "Play",
};

/** The top pick, big: its image, a bold line with the verb in amber, why it's here, and where to
 * open it. */
export function HeroBanner({ item, onWhy, onLike, onOpened }: HeroBannerProps) {
  const type = item.entity_type as ItemType;
  const primary = item.links[0];

  return (
    <section
      aria-labelledby="hero-title"
      className="relative isolate overflow-hidden rounded-2xl bg-ink text-white"
    >
      {item.image_url && (
        <img
          src={item.image_url}
          alt=""
          className="absolute inset-0 -z-10 size-full object-cover object-[center_30%] md:left-[30%] md:w-[70%]"
        />
      )}
      <div
        aria-hidden
        className="absolute inset-0 -z-10 bg-[linear-gradient(0deg,#1a1a1a_8%,#1a1a1acc_40%,#1a1a1a33_100%)] md:bg-[linear-gradient(90deg,#1a1a1a_30%,#1a1a1ae6_45%,#1a1a1a00_80%)]"
      />
      <Button
        variant="onImage"
        size="icon"
        className="absolute top-4 right-4"
        onClick={() => onLike(item)}
        aria-pressed={item.liked}
        aria-label={item.liked ? `Unlike ${item.title}` : `Like ${item.title}`}
      >
        <Heart className={cn("size-5", item.liked && "fill-film text-film")} />
      </Button>
      <div className="flex min-h-[340px] flex-col justify-end gap-4 p-6 md:min-h-[300px] md:max-w-[60%] md:justify-center md:p-10">
        <h1
          id="hero-title"
          className="line-clamp-3 text-[34px] leading-[1.05] font-semibold text-balance text-white md:text-[46px]"
        >
          <span className="text-primary">{VERB_PHRASE[type]}</span> {item.title}
        </h1>
        <p className="max-w-[46ch] text-[15px] leading-relaxed text-white/80">{item.reason}</p>
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px] text-white/70">
          <span className="inline-flex items-center gap-1.5 font-semibold text-white/90">
            <span aria-hidden className={cn("size-1.5 rounded-full", TYPE_META[type].dot)} />
            {TYPE_META[type].label}
            {item.year ? ` · ${item.year}` : ""}
          </span>
          {item.tags.slice(0, 3).map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </p>
        <div className="mt-1 flex flex-wrap items-center gap-2.5">
          {primary && (
            <Button
              asChild
              size="lg"
              className="h-11 px-4 text-[15px] md:h-12 md:px-6 md:text-base"
            >
              <a
                href={primary.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => onOpened(item, primary.platform)}
              >
                {primary.label} <ArrowUpRight />
              </a>
            </Button>
          )}
          <Button
            variant="onImage"
            size="lg"
            className="h-11 px-4 text-[15px] md:h-12 md:px-6 md:text-base"
            onClick={() => onWhy(item)}
            aria-label="Why this?"
          >
            <Info /> <span className="hidden sm:inline">Why this?</span>
          </Button>
        </div>
      </div>
    </section>
  );
}
