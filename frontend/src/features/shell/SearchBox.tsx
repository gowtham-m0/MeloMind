import { useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "cn";
import { Check, Plus, Search, X } from "lucide-react";
import { forwardRef, useId, useState } from "react";

import type { Feed } from "@/shared/api/feed";
import type { FavouriteKind } from "@/shared/api/profiles";
import { searchTaste, type EntityMatch } from "@/shared/api/taste";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { TypeChip } from "@/shared/ui/chip";
import { Thumb } from "@/shared/ui/thumb";
import { useToast } from "@/shared/ui/toast";
import type { ItemType } from "@/shared/ui/types";

import { feedKey } from "../feed/hooks";
import { useAddFavourite } from "../profiles/hooks";

const MIN_QUERY = 2;
const DEBOUNCE_MS = 300;

/**
 * Global search over Qloo: artists, films, shows and books. Adding a result makes it a favourite,
 * which steers the next feed.
 */
export const SearchBox = forwardRef<HTMLInputElement, { profileId: string; className?: string }>(
  function SearchBox({ profileId, className }, ref) {
    const listId = useId();
    const [query, setQuery] = useState("");
    const [added, setAdded] = useState<Set<string>>(new Set());
    const debounced = useDebouncedValue(query.trim(), DEBOUNCE_MS);
    const queryClient = useQueryClient();
    const toast = useToast();
    const addFavourite = useAddFavourite(profileId);

    const results = useQuery({
      queryKey: ["search", debounced],
      queryFn: () => searchTaste(debounced),
      enabled: debounced.length >= MIN_QUERY,
      staleTime: 60_000,
    });
    const open = query.trim().length >= MIN_QUERY;

    async function add(match: EntityMatch) {
      await addFavourite.mutateAsync({
        name: match.name,
        kind: match.type as FavouriteKind,
        entity_id: match.entity_id,
        image_url: match.image_url,
      });
      setAdded((current) => new Set(current).add(match.entity_id));
      queryClient.setQueryData<Feed | null>(feedKey(profileId), (feed) =>
        feed ? { ...feed, stale: true } : feed,
      );
      toast.show(`${match.name} is in your taste. Refresh for new picks.`);
    }

    return (
      <div className={cn("relative", className)}>
        <label className="relative flex items-center">
          <span className="sr-only">Search artists, films, shows and books</span>
          <Search
            className="pointer-events-none absolute left-3.5 size-[18px] text-muted"
            aria-hidden
          />
          <input
            ref={ref}
            type="search"
            role="combobox"
            aria-expanded={open}
            aria-controls={listId}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => event.key === "Escape" && setQuery("")}
            placeholder="Search artists, films, books or anything…"
            className="h-11 w-full rounded-[10px] border border-transparent bg-surface-2 pr-10 pl-11 text-[15px] text-ink placeholder:text-muted focus:border-primary focus:bg-surface"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
              className="absolute right-1.5 grid size-8 place-items-center rounded-lg text-muted hover:bg-surface-3"
            >
              <X className="size-4" />
            </button>
          )}
        </label>

        {open && (
          <div
            id={listId}
            className="rise-in absolute inset-x-0 top-[calc(100%+8px)] z-30 overflow-hidden rounded-xl border border-hairline bg-surface shadow-lift"
          >
            {results.isPending || debounced !== query.trim() ? (
              <p className="p-4 text-sm text-muted">Searching Qloo…</p>
            ) : results.isError ? (
              <p className="p-4 text-sm text-danger">
                Search didn't answer. Try again in a moment.
              </p>
            ) : results.data.length === 0 ? (
              <p className="p-4 text-sm text-muted">
                Nothing for “{query.trim()}”. Try the artist's name.
              </p>
            ) : (
              <ul className="max-h-[60dvh] overflow-y-auto p-1.5">
                {results.data.map((match) => {
                  const done = added.has(match.entity_id);
                  return (
                    <li
                      key={match.entity_id}
                      className="flex items-center gap-3 rounded-lg p-2 hover:bg-surface-2"
                    >
                      <Thumb
                        src={match.image_url}
                        title={match.name}
                        type={match.type as ItemType}
                        aspect="square"
                        round={match.type === "artist"}
                        className="size-11 shrink-0 rounded-lg"
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[15px] font-semibold text-ink">
                          {match.name}
                        </span>
                        <span className="flex items-center gap-2">
                          <TypeChip type={match.type as ItemType} />
                          {match.release_year && (
                            <span className="tabular text-xs text-muted">{match.release_year}</span>
                          )}
                        </span>
                      </span>
                      <button
                        type="button"
                        disabled={done || addFavourite.isPending}
                        onClick={() => void add(match)}
                        className={cn(
                          "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-lg px-3 text-sm font-semibold transition-colors",
                          done
                            ? "text-book-ink"
                            : "bg-primary-tint text-primary-ink hover:bg-primary hover:text-ink",
                        )}
                      >
                        {done ? <Check className="size-4" /> : <Plus className="size-4" />}
                        {done ? "Added" : "Add to my taste"}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        )}
      </div>
    );
  },
);
