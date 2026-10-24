import { ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import { useRef } from "react";
import { Link } from "react-router";

import type { FeedItem, FeedRow } from "@/shared/api/feed";

import { FeedCard } from "./FeedCard";

interface FeedRowViewProps {
  row: FeedRow;
  seeAll?: string;
  onOpen: (item: FeedItem) => void;
  onLike: (item: FeedItem) => void;
  onSave: (item: FeedItem) => void;
  onDismiss: (item: FeedItem) => void;
  onOpened?: (item: FeedItem, platform: string) => void;
}

/** A titled row that scrolls sideways with snap: swipe on phones, arrow buttons on desktop. */
export function FeedRowView({ row, seeAll, ...actions }: FeedRowViewProps) {
  const scroller = useRef<HTMLUListElement>(null);
  const types = new Set(row.items.map((item) => item.entity_type));
  const squares = [...types].every((type) => type === "artist" || type === "song");
  const aspect = squares ? "square" : types.size === 1 ? "poster" : "portrait";
  const headingId = `row-${row.key}-title`;

  function scrollBy(direction: 1 | -1) {
    const element = scroller.current;
    if (element) {
      element.scrollBy({ left: direction * element.clientWidth * 0.85, behavior: "smooth" });
    }
  }

  return (
    <section aria-labelledby={headingId} id={`row-${row.key}`} className="scroll-mt-24">
      <div className="mb-3.5 flex items-end justify-between gap-4">
        <div className="min-w-0">
          <h2 id={headingId} className="truncate text-[22px] leading-tight font-semibold">
            {row.title}
          </h2>
          {row.subtitle && <p className="mt-0.5 truncate text-sm text-muted">{row.subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {seeAll && (
            <Link
              to={seeAll}
              className="mr-1 inline-flex h-9 items-center gap-1 rounded-lg px-2 text-sm font-semibold text-primary-ink hover:bg-primary-tint"
            >
              See all <ArrowRight className="size-4" />
            </Link>
          )}
          <button
            type="button"
            onClick={() => scrollBy(-1)}
            aria-label={`Scroll ${row.title} back`}
            className="hidden size-9 place-items-center rounded-full border border-line text-ink transition-colors hover:bg-surface-2 md:grid"
          >
            <ChevronLeft className="size-[18px]" />
          </button>
          <button
            type="button"
            onClick={() => scrollBy(1)}
            aria-label={`Scroll ${row.title} forward`}
            className="hidden size-9 place-items-center rounded-full border border-line text-ink transition-colors hover:bg-surface-2 md:grid"
          >
            <ChevronRight className="size-[18px]" />
          </button>
        </div>
      </div>
      <ul
        ref={scroller}
        className="no-scrollbar -mx-4 flex snap-x snap-mandatory scroll-px-4 gap-3.5 overflow-x-auto px-4 pt-1 pb-3 md:-mx-1 md:scroll-px-1 md:px-1"
      >
        {row.items.map((item) => (
          <li
            key={item.ref}
            className="w-[calc((100%-2*14px)/2.3)] shrink-0 snap-start sm:w-[calc((100%-4*14px)/4.5)] xl:w-[calc((100%-6*14px)/6.5)]"
          >
            <FeedCard item={item} aspect={aspect} {...actions} />
          </li>
        ))}
      </ul>
    </section>
  );
}
