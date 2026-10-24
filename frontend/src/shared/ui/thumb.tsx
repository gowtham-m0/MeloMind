import { cn } from "cn";
import { useState } from "react";

import { TYPE_META, type ItemType } from "./types";

interface ThumbProps {
  src: string | null | undefined;
  title: string;
  type: ItemType;
  aspect: "square" | "poster" | "wide";
  className?: string;
  /** Load straight away (above the fold) instead of lazily. */
  eager?: boolean;
  /** Round artist images, as music apps do. */
  round?: boolean;
}

const ASPECTS = { square: "aspect-square", poster: "aspect-[2/3]", wide: "aspect-[16/10]" };

/**
 * An item's image at a fixed aspect, so rows never jump. While it loads, and when there's no
 * image or it fails, a designed tile in the type's colour shows the icon and title instead.
 */
export function Thumb({ src, title, type, aspect, className, eager, round }: ThumbProps) {
  const [state, setState] = useState<"loading" | "loaded" | "failed">(src ? "loading" : "failed");
  const meta = TYPE_META[type];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "relative isolate overflow-hidden bg-surface-2",
        ASPECTS[aspect],
        round ? "rounded-full" : "rounded-[10px]",
        className,
      )}
    >
      {state !== "loaded" && (
        <div
          aria-hidden
          className="absolute inset-0 flex flex-col justify-between p-3"
          style={{
            background: `linear-gradient(150deg, color-mix(in oklab, ${meta.color} 26%, white) 0%, color-mix(in oklab, ${meta.color} 58%, white) 100%)`,
          }}
        >
          <Icon className="size-5 text-ink/60" strokeWidth={1.75} />
          {state === "failed" && (
            <span className="line-clamp-3 font-display text-sm leading-tight font-semibold text-ink/80">
              {title}
            </span>
          )}
        </div>
      )}
      {src && state !== "failed" && (
        <img
          src={src}
          alt=""
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          onLoad={() => setState("loaded")}
          onError={() => setState("failed")}
          className={cn(
            "absolute inset-0 size-full object-cover transition-[opacity,filter] duration-500 ease-(--ease-out)",
            state === "loaded" ? "opacity-100 blur-0" : "opacity-0 blur-sm",
          )}
        />
      )}
    </div>
  );
}
