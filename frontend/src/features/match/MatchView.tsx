import { useMutation, useQuery } from "@tanstack/react-query";
import { cn } from "cn";
import { Check, Plus, Search, Users, X } from "lucide-react";
import { useState } from "react";

import { matchTastes, type TasteMatch } from "@/shared/api/ask";
import type { FeedItem } from "@/shared/api/feed";
import { searchTaste, type EntityMatch } from "@/shared/api/taste";
import { useDebouncedValue } from "@/shared/hooks/useDebouncedValue";
import { Button } from "@/shared/ui/button";
import { TagChip } from "@/shared/ui/chip";
import { EmptyState, ErrorState } from "@/shared/ui/states";
import { Thumb } from "@/shared/ui/thumb";

import { FeedRowView } from "../feed/FeedRowView";
import { useItemActions } from "../feed/hooks";
import { useItemParam } from "../item-detail/useItemParam";
import { avatarColour, useProfiles } from "../profiles/hooks";

const FRIEND_MIN = 2;
const FRIEND_MAX = 5;
type Mode = "profile" | "friend";

/** A ring that fills to the match score. */
function ScoreRing({ score }: { score: number }) {
  const percent = Math.round(score * 100);
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  return (
    <div
      role="img"
      aria-label={`${percent} percent match`}
      className="relative grid size-36 shrink-0 place-items-center"
    >
      <svg viewBox="0 0 128 128" className="absolute inset-0 -rotate-90">
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth="10"
          className="stroke-surface-2"
        />
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={circumference * (1 - score)}
          className="stroke-primary transition-[stroke-dashoffset] duration-700 ease-out"
        />
      </svg>
      <span className="font-display text-4xl font-semibold text-ink tabular-nums">
        {percent}
        <span className="text-xl text-muted">%</span>
      </span>
    </div>
  );
}

/** Search Qloo for a friend's favourites, up to five. */
function FriendPicker({
  chosen,
  onChange,
}: {
  chosen: EntityMatch[];
  onChange: (next: EntityMatch[]) => void;
}) {
  const [query, setQuery] = useState("");
  const debounced = useDebouncedValue(query.trim(), 300);
  const results = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => searchTaste(debounced),
    enabled: debounced.length >= 2,
    staleTime: 60_000,
  });
  const has = (match: EntityMatch) => chosen.some((item) => item.entity_id === match.entity_id);
  const full = chosen.length >= FRIEND_MAX;

  return (
    <div className="flex flex-col gap-3">
      <label className="relative flex items-center">
        <span className="sr-only">Search a friend's favourite</span>
        <Search className="pointer-events-none absolute left-3.5 size-[18px] text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search a friend's favourite artist, film, show or book…"
          className="h-12 w-full rounded-[10px] bg-surface-2 pr-4 pl-10 text-base text-ink outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-primary/50"
        />
      </label>
      {chosen.length > 0 && (
        <ul aria-label="Your friend's favourites" className="flex flex-wrap gap-2">
          {chosen.map((match) => (
            <li key={match.entity_id}>
              <button
                type="button"
                onClick={() =>
                  onChange(chosen.filter((item) => item.entity_id !== match.entity_id))
                }
                aria-label={`Remove ${match.name}`}
                className="inline-flex h-11 items-center gap-1.5 rounded-full border border-primary bg-primary-tint pr-3 pl-4 text-sm font-medium text-ink"
              >
                {match.name} <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {results.isFetching && <p className="text-sm text-muted">Searching…</p>}
      {results.isError && <p className="text-sm text-film-ink">Search didn't work. Try again.</p>}
      {debounced.length >= 2 && results.data && results.data.length > 0 && (
        <ul className="flex flex-col divide-y divide-hairline rounded-xl border border-hairline">
          {results.data.slice(0, 6).map((match) => (
            <li key={match.entity_id} className="flex items-center gap-3 p-2.5">
              <Thumb
                src={match.image_url}
                title={match.name}
                type={match.type}
                aspect="square"
                className="size-11 shrink-0"
              />
              <span className="min-w-0 flex-1 truncate text-[15px] font-medium text-ink">
                {match.name}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={has(match) || full}
                onClick={() => onChange([...chosen, match])}
              >
                {has(match) ? <Check /> : <Plus />} {has(match) ? "Added" : "Add"}
              </Button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-sm text-muted">
        Add {FRIEND_MIN} to {FRIEND_MAX}. {chosen.length}/{FRIEND_MAX} so far.
      </p>
    </div>
  );
}

/** The score, the shared tags and the "For you both" row. */
function Result({ profileId, match }: { profileId: string; match: TasteMatch }) {
  const actions = useItemActions(profileId);
  const { open } = useItemParam();
  const hasShared = match.shared_tags.length > 0;
  return (
    <div className="rise-in flex flex-col gap-8">
      <section className="flex flex-col items-start gap-6 rounded-2xl border border-hairline bg-surface p-6 shadow-soft sm:flex-row sm:items-center">
        <ScoreRing score={match.score} />
        <div className="min-w-0">
          <h2 className="text-[24px] font-semibold">
            {hasShared ? "What you have in common" : "Not much overlap yet"}
          </h2>
          {hasShared ? (
            <ul aria-label="Shared tags" className="mt-3 flex flex-wrap gap-2">
              {match.shared_tags.map((tag) => (
                <li key={tag}>
                  <TagChip className="border-primary bg-primary-tint text-ink">{tag}</TagChip>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-2 max-w-prose text-body">
              No shared tags, so the row below is simply what's popular. Add a few more favourites
              and try again.
            </p>
          )}
        </div>
      </section>
      {match.row.items.length > 0 && (
        <FeedRowView
          row={match.row}
          onOpen={(item: FeedItem) => open(item.ref)}
          onLike={(item) => void actions.toggleLike(item)}
          onSave={(item) => void actions.toggleSave(item)}
          onDismiss={(item) => void actions.notInterested(item)}
          onOpened={actions.opened}
        />
      )}
    </div>
  );
}

/** Taste match: compare this profile with another one of yours, or with a friend's favourites. */
export function MatchView({ profileId }: { profileId: string }) {
  const profiles = useProfiles();
  const [mode, setMode] = useState<Mode>("profile");
  const [otherId, setOtherId] = useState<string | null>(null);
  const [friend, setFriend] = useState<EntityMatch[]>([]);
  const compare = useMutation({
    mutationFn: () =>
      mode === "profile"
        ? matchTastes(profileId, { other_profile_id: otherId ?? undefined })
        : matchTastes(profileId, { favourites: friend.map((match) => match.entity_id) }),
  });

  const others = (profiles.data ?? []).filter((profile) => profile.id !== profileId);
  const ready = mode === "profile" ? otherId !== null : friend.length >= FRIEND_MIN;

  return (
    <div className="flex max-w-4xl flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-[34px] leading-[1.1] font-semibold md:text-[44px]">
          How alike are two tastes?
        </h1>
        <p className="max-w-prose text-lg text-body">
          Qloo compares what two people love, finds the tags they share and builds a row you'd both
          enjoy.
        </p>
      </header>

      <div
        role="group"
        aria-label="Compare with"
        className="flex w-fit rounded-full bg-surface-2 p-1"
      >
        {(
          [
            ["profile", "One of my profiles"],
            ["friend", "A friend's favourites"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            type="button"
            aria-pressed={mode === value}
            onClick={() => {
              setMode(value);
              compare.reset();
            }}
            className={cn(
              "h-11 rounded-full px-4 text-sm font-semibold transition-colors",
              mode === value ? "bg-surface text-ink shadow-soft" : "text-muted",
            )}
          >
            {label}
          </button>
        ))}
      </div>

      {mode === "profile" ? (
        profiles.isError ? (
          <ErrorState error={profiles.error} onRetry={() => void profiles.refetch()} />
        ) : others.length === 0 && !profiles.isPending ? (
          <EmptyState title="You only have one profile">
            Add another profile from the profile menu, or compare with a friend's favourites.
          </EmptyState>
        ) : (
          <ul aria-label="Profiles" className="flex flex-wrap gap-3">
            {others.map((profile) => (
              <li key={profile.id}>
                <button
                  type="button"
                  aria-pressed={otherId === profile.id}
                  onClick={() => setOtherId(profile.id)}
                  className={cn(
                    "flex h-16 items-center gap-3 rounded-2xl border pr-5 pl-3 text-left transition-colors",
                    otherId === profile.id
                      ? "border-primary bg-primary-tint"
                      : "border-line bg-surface hover:border-[#c9c9c9]",
                  )}
                >
                  <span
                    className={cn(
                      "grid size-10 place-items-center rounded-full font-display text-lg font-semibold text-ink",
                      avatarColour(profile.id),
                    )}
                  >
                    {profile.display_name.slice(0, 1).toUpperCase()}
                  </span>
                  <span className="text-[15px] font-semibold text-ink">{profile.display_name}</span>
                </button>
              </li>
            ))}
          </ul>
        )
      ) : (
        <FriendPicker chosen={friend} onChange={setFriend} />
      )}

      <div>
        <Button size="lg" disabled={!ready || compare.isPending} onClick={() => compare.mutate()}>
          <Users /> {compare.isPending ? "Comparing…" : "Compare tastes"}
        </Button>
      </div>

      {compare.isError && (
        <ErrorState
          title="Couldn't compare those"
          error={compare.error}
          onRetry={() => compare.mutate()}
        />
      )}
      {compare.data && <Result profileId={profileId} match={compare.data} />}
    </div>
  );
}
