import { cn } from "cn";
import { ChevronRight } from "lucide-react";
import { useId } from "react";

import type { FeedItem, FeedRow } from "@/shared/api/feed";
import { Thumb } from "@/shared/ui/thumb";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

const STAGGER_MS = 90;

/** The source of a thread: the title the row says it comes from ("Because you like X…"). */
function sourceTitle(row: FeedRow): string | null {
  const fromItems = row.items.find((item) => item.because_of)?.because_of?.title;
  if (fromItems) {
    return fromItems;
  }
  const match = /like (.+?)…?$/.exec(row.subtitle);
  return match ? match[1] : null;
}

/**
 * The signature move: one thread from something you love, through a pick of each other type,
 * each strand in the colour of the type it reaches. It grows in once when the feed arrives.
 */
export function TasteThread({ row, onOpen }: { row: FeedRow; onOpen: (item: FeedItem) => void }) {
  const source = sourceTitle(row);
  const titleId = useId();

  return (
    <section
      aria-labelledby={titleId}
      className="rounded-xl border border-hairline bg-surface p-4 shadow-soft"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        Cross-culture picks
      </h2>
      <p className="mt-0.5 text-sm text-muted">One taste, four ways to enjoy it.</p>

      <ol className="mt-4 flex flex-col">
        {source && (
          <li className="relative flex items-center gap-3 pb-1">
            <span
              aria-hidden
              className="thread-node relative z-10 ml-[19px] grid size-3.5 place-items-center rounded-full bg-ink ring-4 ring-surface"
            />
            <span className="text-sm text-body">
              Because you like <span className="font-semibold text-ink">{source}</span>
            </span>
          </li>
        )}
        {row.items.map((item, index) => {
          const type = item.entity_type as ItemType;
          const meta = TYPE_META[type];
          const previous =
            index === 0
              ? "var(--ink)"
              : TYPE_META[row.items[index - 1].entity_type as ItemType].color;
          const delay = `${(index + 1) * STAGGER_MS}ms`;
          return (
            <li key={item.ref} className="relative">
              <span
                aria-hidden
                className="thread-segment absolute top-[-22px] left-[24px] h-[46px] w-[3px] rounded-full"
                style={{
                  background: `linear-gradient(${previous}, ${meta.color})`,
                  animationDelay: delay,
                }}
              />
              <button
                type="button"
                onClick={() => onOpen(item)}
                className="group relative flex w-full items-center gap-3 rounded-lg py-2 pr-1 text-left transition-colors hover:bg-surface-2"
              >
                <span
                  aria-hidden
                  className={cn(
                    "thread-node relative z-10 ml-[19px] size-3.5 shrink-0 rounded-full ring-4 ring-surface",
                    meta.dot,
                  )}
                  style={{ animationDelay: delay }}
                />
                <Thumb
                  src={item.image_url}
                  title={item.title}
                  type={type}
                  aspect="square"
                  round={type === "artist"}
                  className="size-12 shrink-0 rounded-lg"
                />
                <span className="min-w-0 flex-1">
                  <span
                    className={cn("block text-xs font-semibold tracking-wide uppercase", meta.text)}
                  >
                    {meta.verb}
                  </span>
                  <span className="block truncate text-[15px] font-semibold text-ink">
                    {item.title}
                  </span>
                </span>
                <ChevronRight className="size-4 shrink-0 text-muted transition-transform duration-150 group-hover:translate-x-0.5" />
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
