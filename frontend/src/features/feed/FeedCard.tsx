import { cn } from "cn";
import { Bookmark, Heart, X } from "lucide-react";

import type { FeedItem } from "@/shared/api/feed";
import { TypeChip } from "@/shared/ui/chip";
import { Thumb } from "@/shared/ui/thumb";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

interface FeedCardProps {
  item: FeedItem;
  aspect: "square" | "poster" | "portrait";
  onOpen: (item: FeedItem) => void;
  onLike: (item: FeedItem) => void;
  onSave: (item: FeedItem) => void;
  onDismiss: (item: FeedItem) => void;
  className?: string;
}

const iconButton =
  "grid size-9 place-items-center rounded-full bg-white/90 text-ink shadow-soft backdrop-blur transition-[background-color,color,transform] duration-150 hover:bg-white active:scale-95";

/**
 * One recommendation: image, type, title, year, and the taste thread back to its source (or its
 * reason when it has none). Tapping opens the detail
 * sheet; the heart is always reachable, save and "not interested" appear on hover or focus.
 */
export function FeedCard({
  item,
  aspect,
  onOpen,
  onLike,
  onSave,
  onDismiss,
  className,
}: FeedCardProps) {
  const type = item.entity_type as ItemType;
  return (
    <article className={cn("group/card relative flex flex-col gap-2.5", className)}>
      <div className="lift relative rounded-[10px]">
        <button
          type="button"
          onClick={() => onOpen(item)}
          className="block w-full rounded-[10px] text-left"
          aria-label={`${item.title}: details`}
        >
          <Thumb
            src={item.image_url}
            title={item.title}
            type={type}
            aspect={aspect === "portrait" ? "poster" : aspect}
            className={aspect === "portrait" ? "aspect-[3/4]" : undefined}
          />
        </button>
        <div className="absolute top-2 right-2 flex flex-col gap-1.5">
          <button
            type="button"
            onClick={() => onLike(item)}
            aria-pressed={item.liked}
            aria-label={item.liked ? `Unlike ${item.title}` : `Like ${item.title}`}
            className={cn(iconButton, item.liked && "text-film")}
          >
            <Heart className={cn("size-[18px]", item.liked && "fill-current")} />
          </button>
          <button
            type="button"
            onClick={() => onSave(item)}
            aria-pressed={item.saved}
            aria-label={item.saved ? `Unsave ${item.title}` : `Save ${item.title}`}
            className={cn(
              iconButton,
              "opacity-0 group-focus-within/card:opacity-100 group-hover/card:opacity-100 pointer-coarse:opacity-100",
              item.saved && "text-primary-ink opacity-100",
            )}
          >
            <Bookmark className={cn("size-[18px]", item.saved && "fill-current")} />
          </button>
          <button
            type="button"
            onClick={() => onDismiss(item)}
            aria-label={`Not interested in ${item.title}`}
            className={cn(
              iconButton,
              "opacity-0 group-focus-within/card:opacity-100 group-hover/card:opacity-100 pointer-coarse:hidden",
            )}
          >
            <X className="size-[18px]" />
          </button>
        </div>
      </div>
      <div className="flex flex-col gap-1 px-0.5">
        <div className="flex items-center gap-2">
          <TypeChip type={type} />
          {item.year && <span className="tabular text-xs text-muted">{item.year}</span>}
        </div>
        <h3 className="line-clamp-2 font-sans text-[15px] leading-snug font-semibold tracking-normal text-ink">
          {item.title}
        </h3>
        {item.because_of ? (
          <p className="flex min-w-0 items-center gap-1.5 text-[13px] leading-snug text-muted">
            <span
              aria-hidden
              className="h-[3px] w-4 shrink-0 rounded-full"
              style={{ background: `linear-gradient(90deg, var(--ink), ${TYPE_META[type].color})` }}
            />
            <span className="sr-only">Because of </span>
            <span className="truncate">{item.because_of.title}</span>
          </p>
        ) : (
          <p className="line-clamp-2 text-[13px] leading-snug text-muted">{item.reason}</p>
        )}
      </div>
    </article>
  );
}
