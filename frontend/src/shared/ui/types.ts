import { AudioLines, BookOpen, Clapperboard, Music2, Tv, type LucideIcon } from "lucide-react";

/** The kinds of card. Qloo picks artists, films, TV and books; a song is a top track of an
 * artist Qloo picked, looked up in Apple's catalogue. */
export type ItemType = "artist" | "movie" | "tv_show" | "book" | "song";

interface TypeMeta {
  /** Singular label for chips. */
  label: string;
  /** Plural label for row and tab titles. */
  plural: string;
  /** What you do with it, for the cross-culture thread. */
  verb: "Listen" | "Watch" | "Read";
  icon: LucideIcon;
  /** Tailwind classes for the type's colour, as fill, text on white, and a soft tint. */
  dot: string;
  text: string;
  tint: string;
  /** The type's colour as a CSS value, for strokes and gradients. */
  color: string;
}

/** Labels, icons and colours per item type. Type colours carry meaning only. */
export const TYPE_META: Record<ItemType, TypeMeta> = {
  artist: {
    label: "Music",
    plural: "Music",
    verb: "Listen",
    icon: Music2,
    dot: "bg-music",
    text: "text-music-ink",
    tint: "bg-music/15",
    color: "var(--music)",
  },
  movie: {
    label: "Film",
    plural: "Films",
    verb: "Watch",
    icon: Clapperboard,
    dot: "bg-film",
    text: "text-film-ink",
    tint: "bg-film/12",
    color: "var(--film)",
  },
  tv_show: {
    label: "TV",
    plural: "TV shows",
    verb: "Watch",
    icon: Tv,
    dot: "bg-tv",
    text: "text-tv-ink",
    tint: "bg-tv/12",
    color: "var(--tv)",
  },
  song: {
    label: "Song",
    plural: "Songs",
    verb: "Listen",
    icon: AudioLines,
    dot: "bg-music",
    text: "text-music-ink",
    tint: "bg-music/15",
    color: "var(--music)",
  },
  book: {
    label: "Book",
    plural: "Books",
    verb: "Read",
    icon: BookOpen,
    dot: "bg-book",
    text: "text-book-ink",
    tint: "bg-book/12",
    color: "var(--book)",
  },
};

/** The four types Qloo recommends, in the order used for tabs, tiles and the thread. */
export const ITEM_TYPES: ItemType[] = ["artist", "movie", "tv_show", "book"];
