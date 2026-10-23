import { useId, useRef, useState } from "react";
import { cn } from "cn";

import { QlooModeBadge } from "@/features/health/QlooModeBadge";
import type { FavouriteCreate, FavouriteKind } from "@/shared/api/profiles";
import type { EntityMatch } from "@/shared/api/taste";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { ErrorBanner, LoadingState } from "@/shared/ui/states";
import { ITEM_TYPE_LABELS, TypeIcon } from "@/shared/ui/type-icon";

import { MIN_QUERY_LENGTH, useAddFavourite, useTasteSearch } from "./hooks";

const SEARCH_DEBOUNCE_MS = 300;

const KINDS: FavouriteKind[] = ["artist", "song", "movie", "tv_show", "book"];

const SEARCH_LABELS: Record<FavouriteKind, string> = {
  artist: "Search for a singer, band or composer",
  song: "Who sang it? Search for the singer",
  movie: "Search for a film",
  tv_show: "Search for a TV show",
  book: "Search for a book",
};

interface Singer {
  name: string;
  entityId: string | null;
}

/**
 * Adds favourites through taste search. Tapping a match saves it as verified; anything not
 * found can be kept as text. A song is found through its singer, then its title is typed.
 */
export function FavouritesEditor({ profileId }: { profileId: string }) {
  const id = useId();
  const [kind, setKind] = useState<FavouriteKind>("artist");
  const [query, setQuery] = useState("");
  const [singer, setSinger] = useState<Singer | null>(null);
  const [songTitle, setSongTitle] = useState("");
  const [announcement, setAnnouncement] = useState("");
  const songTitleRef = useRef<HTMLInputElement>(null);

  const trimmed = query.trim();
  const debounced = useDebouncedValue(trimmed, SEARCH_DEBOUNCE_MS);
  const search = useTasteSearch(debounced, kind, singer === null);
  const add = useAddFavourite(profileId);

  function reset(nextKind: FavouriteKind = kind) {
    setKind(nextKind);
    setQuery("");
    setSinger(null);
    setSongTitle("");
    add.reset();
  }

  function save(body: FavouriteCreate) {
    add.mutate(body, {
      onSuccess: (favourite) => {
        const title = favourite.song_title ? `“${favourite.song_title}” by ` : "";
        setAnnouncement(`Saved ${title}${favourite.name}.`);
        reset();
      },
    });
  }

  function pickSinger(next: Singer) {
    setSinger(next);
    window.setTimeout(() => songTitleRef.current?.focus(), 0);
  }

  function pick(match: EntityMatch) {
    if (kind === "song") {
      pickSinger({ name: match.name, entityId: match.entity_id });
    } else {
      save({ name: match.name, kind, entity_id: match.entity_id });
    }
  }

  function keepAsText() {
    if (kind === "song") {
      pickSinger({ name: trimmed, entityId: null });
    } else {
      save({ name: trimmed, kind });
    }
  }

  return (
    <section aria-labelledby={`${id}-title`} className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={`${id}-title`} className="text-2xl font-semibold">
          Add a favourite
        </h2>
        <QlooModeBadge />
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 text-lg font-bold">What kind of favourite?</legend>
        <div className="flex flex-wrap gap-2">
          {KINDS.map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={kind === option}
              onClick={() => reset(option)}
              className={cn(
                "inline-flex min-h-11 items-center gap-2 rounded-full border-2 px-4 text-lg",
                kind === option
                  ? "border-primary bg-primary text-primary-foreground"
                  : "border-input bg-card hover:bg-accent",
              )}
            >
              <TypeIcon type={option} />
              {ITEM_TYPE_LABELS[option]}
            </button>
          ))}
        </div>
      </fieldset>

      {singer === null ? (
        <div className="flex flex-col gap-3">
          <Label htmlFor={`${id}-search`}>{SEARCH_LABELS[kind]}</Label>
          {kind === "song" && (
            <p className="text-muted-foreground">
              Songs are found through the singer. You'll type the song title next.
            </p>
          )}
          <Input
            id={`${id}-search`}
            type="search"
            autoComplete="off"
            value={query}
            maxLength={100}
            onChange={(event) => setQuery(event.target.value)}
            aria-describedby={`${id}-results-status`}
          />
          <SearchResults
            statusId={`${id}-results-status`}
            query={debounced}
            typing={trimmed !== debounced}
            search={search}
            onPick={pick}
            pickHint={kind === "song" ? "Tap the singer" : "Tap one to save"}
            disabled={add.isPending}
          />
          {trimmed.length > 0 && (
            <Button
              type="button"
              variant="link"
              className="self-start px-0"
              onClick={keepAsText}
              disabled={add.isPending}
            >
              Not found? Keep “{trimmed}” as text
            </Button>
          )}
        </div>
      ) : (
        <form
          className="flex flex-col gap-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (songTitle.trim()) {
              save({
                name: singer.name,
                kind: "song",
                entity_id: singer.entityId,
                song_title: songTitle.trim(),
              });
            }
          }}
        >
          <p>
            Singer: <strong>{singer.name}</strong>{" "}
            <span className="text-muted-foreground">
              ({singer.entityId ? "matched" : "kept as text"})
            </span>
          </p>
          <Label htmlFor={`${id}-song`}>Song title</Label>
          <Input
            ref={songTitleRef}
            id={`${id}-song`}
            autoComplete="off"
            value={songTitle}
            maxLength={120}
            onChange={(event) => setSongTitle(event.target.value)}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={!songTitle.trim() || add.isPending}>
              Save song
            </Button>
            <Button type="button" variant="outline" onClick={() => reset()}>
              Choose another singer
            </Button>
          </div>
        </form>
      )}

      {add.isError && <ErrorBanner error={add.error} title="Couldn't save that favourite" />}
      <p aria-live="polite" className="font-bold text-primary">
        {announcement}
      </p>
    </section>
  );
}

interface SearchResultsProps {
  statusId: string;
  query: string;
  typing: boolean;
  search: ReturnType<typeof useTasteSearch>;
  onPick: (match: EntityMatch) => void;
  pickHint: string;
  disabled: boolean;
}

function SearchResults({
  statusId,
  query,
  typing,
  search,
  onPick,
  pickHint,
  disabled,
}: SearchResultsProps) {
  if (query.length < MIN_QUERY_LENGTH) {
    return <p id={statusId} className="sr-only" />;
  }
  if (search.isPending || typing) {
    return (
      <div id={statusId}>
        <LoadingState label="Searching…" />
      </div>
    );
  }
  if (search.isError) {
    return (
      <div id={statusId}>
        <ErrorBanner
          error={search.error}
          title="Search didn't work"
          onRetry={() => void search.refetch()}
        />
      </div>
    );
  }
  if (search.data.length === 0) {
    return (
      <p id={statusId} role="status">
        No matches for “{query}”.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      <p id={statusId} role="status" className="text-muted-foreground">
        {search.data.length === 1 ? "1 match" : `${search.data.length} matches`}. {pickHint}.
      </p>
      <ul className="flex flex-col gap-2">
        {search.data.map((match) => (
          <li key={match.entity_id}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onPick(match)}
              className="flex min-h-14 w-full items-center gap-3 rounded-lg border-2 bg-card px-4 py-2 text-left hover:bg-accent disabled:opacity-50"
            >
              <TypeIcon type={match.type} className="size-6 text-primary" />
              <span className="flex flex-1 flex-col">
                <span className="font-bold">{match.name}</span>
                <span className="text-base text-muted-foreground">
                  {ITEM_TYPE_LABELS[match.type]}
                  {match.release_year ? ` · ${match.release_year}` : ""}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
