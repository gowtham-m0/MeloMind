import { useQuery } from "@tanstack/react-query";
import { cn } from "cn";
import { ArrowRight, Check, Search, X } from "lucide-react";
import { useId, useState } from "react";

import { removeFavourite, type FavouriteKind } from "@/shared/api/profiles";
import { searchTaste, type EntityMatch } from "@/shared/api/taste";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { Button } from "@/shared/ui/button";
import { TypeChip } from "@/shared/ui/chip";
import { Thumb } from "@/shared/ui/thumb";
import { ITEM_TYPES, TYPE_META, type ItemType } from "@/shared/ui/types";

import { RememberBox } from "../favourites/RememberBox";
import { useAddFavourite } from "../profiles/hooks";

const GOAL = 3;
const MIN_QUERY = 2;
const DEBOUNCE_MS = 300;
const EXAMPLES = ["Arctic Monkeys", "Interstellar", "Succession", "Dune"];

type Filter = "all" | ItemType;

/** A favourite picked in this step, so a second tap can undo it. */
interface Picked {
  match: EntityMatch;
  favouriteId: string;
}

interface StepFavouritesProps {
  profileId: string;
  name: string;
  onNext: () => void;
}

/**
 * Step 3: search Qloo and tap to add favourites. Each one is saved on the spot as a verified
 * favourite, so the first feed starts from real taste, not from what's popular.
 */
export function StepFavourites({ profileId, name, onNext }: StepFavouritesProps) {
  const listId = useId();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [picked, setPicked] = useState<Map<string, Picked>>(new Map());
  const [failed, setFailed] = useState(false);
  const addFavourite = useAddFavourite(profileId);
  const debounced = useDebouncedValue(query.trim(), DEBOUNCE_MS);
  const searching = debounced.length >= MIN_QUERY;

  const results = useQuery({
    queryKey: ["search", debounced, filter],
    queryFn: () => searchTaste(debounced, filter === "all" ? undefined : (filter as FavouriteKind)),
    enabled: searching,
    staleTime: 60_000,
  });

  async function toggle(match: EntityMatch) {
    setFailed(false);
    const existing = picked.get(match.entity_id);
    try {
      if (existing) {
        await removeFavourite(profileId, existing.favouriteId);
        setPicked((current) => {
          const next = new Map(current);
          next.delete(match.entity_id);
          return next;
        });
        return;
      }
      const favourite = await addFavourite.mutateAsync({
        name: match.name,
        kind: match.type as FavouriteKind,
        entity_id: match.entity_id,
        image_url: match.image_url,
      });
      setPicked((current) =>
        new Map(current).set(match.entity_id, { match, favouriteId: favourite.id }),
      );
    } catch {
      setFailed(true);
    }
  }

  const count = picked.size;
  const remaining = Math.max(GOAL - count, 0);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[36px] leading-tight font-semibold md:text-[44px]">
          What do you <span className="text-primary">love</span>, {name}?
        </h1>
        <p className="mt-2 max-w-[52ch] text-lg text-body">
          Search artists, films, shows and books, and tap the ones you'd recommend to a friend. Aim
          for {GOAL} or more.
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <label className="relative flex items-center">
          <span className="sr-only">Search artists, films, shows and books</span>
          <Search
            className="pointer-events-none absolute left-3.5 size-[18px] text-muted"
            aria-hidden
          />
          <input
            type="search"
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search artists, films, shows or books…"
            aria-controls={listId}
            className="h-12 w-full rounded-[10px] border border-transparent bg-surface-2 pr-10 pl-11 text-base text-ink placeholder:text-muted focus:border-primary focus:bg-surface"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
              className="absolute right-1 grid size-11 place-items-center rounded-lg text-muted hover:bg-surface-3"
            >
              <X className="size-4" />
            </button>
          )}
        </label>
        <div role="group" aria-label="Search in" className="flex flex-wrap gap-2">
          {(["all", ...ITEM_TYPES] as Filter[]).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={filter === option}
              onClick={() => setFilter(option)}
              className={cn(
                "inline-flex h-11 items-center rounded-full border px-4 text-sm font-medium transition-colors duration-200",
                filter === option
                  ? "border-primary bg-primary text-ink"
                  : "border-line bg-surface text-body hover:border-[#c9c9c9] hover:text-ink",
              )}
            >
              {option === "all" ? "Everything" : TYPE_META[option].plural}
            </button>
          ))}
        </div>
      </div>

      <div id={listId} aria-live="polite" className="min-h-48">
        {!searching ? (
          <div className="rounded-2xl border border-dashed border-line bg-surface-2/60 p-6">
            <p className="font-semibold text-ink">Not sure where to start?</p>
            <p className="mt-1 text-body">Try one of these, or type anything you like.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => setQuery(example)}
                  className="inline-flex h-11 items-center rounded-full border border-line bg-surface px-4 text-sm text-body transition-colors hover:border-[#c9c9c9] hover:text-ink"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        ) : results.isPending || debounced !== query.trim() ? (
          <p className="py-6 text-muted">Searching Qloo…</p>
        ) : results.isError ? (
          <p role="alert" className="py-6 text-danger">
            Search didn't answer. Try again in a moment.
          </p>
        ) : results.data.length === 0 ? (
          <p className="py-6 text-muted">Nothing for “{debounced}”. Try the exact name.</p>
        ) : (
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {results.data.map((match) => {
              const type = match.type as ItemType;
              const isPicked = picked.has(match.entity_id);
              return (
                <li key={match.entity_id}>
                  <button
                    type="button"
                    aria-pressed={isPicked}
                    onClick={() => void toggle(match)}
                    className="flex w-full flex-col gap-2 text-left"
                  >
                    <span className="lift relative block rounded-[10px]">
                      <Thumb
                        src={match.image_url}
                        title={match.name}
                        type={type}
                        aspect={type === "artist" ? "square" : "poster"}
                        className={cn(isPicked && "ring-[3px] ring-primary ring-offset-2")}
                      />
                      <span
                        aria-hidden
                        className={cn(
                          "absolute top-2 right-2 grid size-8 place-items-center rounded-full bg-primary text-ink shadow-soft transition-[opacity,transform] duration-200 ease-(--ease-out)",
                          isPicked ? "scale-100 opacity-100" : "scale-90 opacity-0",
                        )}
                      >
                        <Check className="size-[18px]" />
                      </span>
                    </span>
                    <span className="flex flex-col gap-0.5 px-0.5">
                      <TypeChip type={type} />
                      <span className="line-clamp-2 text-[15px] leading-snug font-semibold text-ink">
                        {match.name}
                      </span>
                      {match.release_year && (
                        <span className="tabular text-xs text-muted">{match.release_year}</span>
                      )}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {failed && (
        <p role="alert" className="text-danger">
          That didn't save. Tap it again.
        </p>
      )}

      <RememberBox profileId={profileId} />

      <div className="sticky bottom-0 -mx-5 flex flex-wrap items-center gap-4 border-t border-hairline bg-surface/90 px-5 py-4 backdrop-blur-md md:-mx-8 md:px-8">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <ul aria-label="Your picks" className="flex -space-x-2">
            {[...picked.values()].slice(-5).map(({ match }) => (
              <li key={match.entity_id}>
                <Thumb
                  src={match.image_url}
                  title={match.name}
                  type={match.type as ItemType}
                  aspect="square"
                  round
                  className="size-9 ring-2 ring-surface"
                />
              </li>
            ))}
          </ul>
          <p className="text-sm text-body" aria-live="polite">
            {count === 0
              ? `Pick ${GOAL} to start`
              : remaining > 0
                ? `${count} picked, ${remaining} more is ideal`
                : `${count} picked. Nice taste.`}
          </p>
        </div>
        <Button variant="ghost" onClick={onNext}>
          {count === 0 ? "Skip" : "Skip the rest"}
        </Button>
        <Button size="lg" disabled={count === 0} onClick={onNext}>
          Next: this or that <ArrowRight />
        </Button>
      </div>
    </div>
  );
}
