import type { FeedItem } from "@/shared/api/feed";

import { useItemParam } from "../item-detail/useItemParam";

import { FeedCard } from "./FeedCard";
import { useItemActions } from "./hooks";

/** A responsive grid of cards, for Discover and Saved. */
export function CardGrid({ profileId, items }: { profileId: string; items: FeedItem[] }) {
  const actions = useItemActions(profileId);
  const { open } = useItemParam();
  const types = new Set(items.map((item) => item.entity_type));
  const squares = items.every(
    (item) => item.entity_type === "artist" || item.entity_type === "song",
  );
  const aspect = squares ? "square" : types.size === 1 ? "poster" : "portrait";
  return (
    <ul className="grid grid-cols-2 gap-x-3.5 gap-y-6 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-6">
      {items.map((item, index) => (
        <li
          key={item.ref}
          className="rise-in"
          style={{ animationDelay: `${Math.min(index, 12) * 30}ms` }}
        >
          <FeedCard
            item={item}
            aspect={aspect}
            onOpen={(card) => open(card.ref)}
            onLike={(card) => void actions.toggleLike(card)}
            onSave={(card) => void actions.toggleSave(card)}
            onDismiss={(card) => void actions.notInterested(card)}
            onOpened={actions.opened}
          />
        </li>
      ))}
    </ul>
  );
}
