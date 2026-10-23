import type { ReactNode } from "react";

import { formatLength } from "@/features/player/format";
import type { SessionItem } from "@/shared/api/sessions";
import { decadeClass, decadeOf } from "@/shared/ui/decade";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

import { ageLine } from "./labels";
import { SourceBadge } from "./SourceBadge";

interface ItemCardProps {
  item: SessionItem;
  firstName: string;
  /** Buttons and editors for the caregiver, shown under the details. */
  children?: ReactNode;
}

/** One session item for the caregiver: what it is, why it was picked, and how it plays. */
export function ItemCard({ item, firstName, children }: ItemCardProps) {
  const age = ageLine(item, firstName);
  return (
    <article className="flex overflow-hidden rounded-lg border-2 bg-card">
      <div
        aria-hidden="true"
        className={`w-3 shrink-0 ${decadeClass(decadeOf(item.release_year))}`}
      />
      <div className="flex min-w-0 flex-1 flex-col gap-3 p-4">
        <div className="flex flex-wrap items-center gap-3">
          <TypeIcon type={item.entity_type} className="size-6 text-primary" />
          <h3 className="text-xl font-bold">{item.title}</h3>
          <SourceBadge source={item.source} />
        </div>
        <p className="text-base text-muted-foreground">
          {ITEM_TYPE_LABELS[item.entity_type]}
          {item.release_year != null && ` · ${item.release_year}`}
          {" · "}
          {item.media
            ? `${item.media.provider === "demo" ? "Demo media" : "Video"}, ${formatLength(item.duration_s)}`
            : `No video: a ${formatLength(item.duration_s)} conversation`}
        </p>
        {age && <p className="font-semibold">{age}.</p>}
        {item.reason && <p>{item.reason}</p>}
        {children}
      </div>
    </article>
  );
}
