import { cn } from "cn";

/** Every kind of item a card can show. */
export type ItemType = "artist" | "song" | "movie" | "tv_show" | "book";

/** Plain-English names for item types. */
export const ITEM_TYPE_LABELS: Record<ItemType, string> = {
  artist: "Artist",
  song: "Song",
  movie: "Film",
  tv_show: "TV show",
  book: "Book",
};

// Stroke icons from Lucide (ISC licence): mic, music, film, tv and book-open.
const PATHS: Record<ItemType, string[]> = {
  artist: [
    "M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z",
    "M19 10v2a7 7 0 0 1-14 0v-2",
    "M12 19v3",
  ],
  song: [
    "M9 18V5l12-2v13",
    "M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
    "M21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z",
  ],
  movie: [
    "M4 2h16a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z",
    "M7 2v20M17 2v20M2 12h20M2 7h5M2 17h5M17 17h5M17 7h5",
  ],
  tv_show: [
    "M4 7h16a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2Z",
    "m17 2-5 5-5-5",
  ],
  book: ["M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z", "M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"],
};

interface TypeIconProps {
  type: ItemType;
  className?: string;
}

/** The icon for an item type. Decorative: always pair it with a text label. */
export function TypeIcon({ type, className }: TypeIconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={cn("size-5 shrink-0", className)}
    >
      {PATHS[type].map((d) => (
        <path key={d} d={d} />
      ))}
    </svg>
  );
}
