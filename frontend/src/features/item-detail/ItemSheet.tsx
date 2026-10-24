import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "cn";
import { ArrowUpRight, Bookmark, Heart, Play, X } from "lucide-react";

import { getItem, previewItem, type Feed, type FeedItem } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { SourceBadge, TagChip, TypeChip } from "@/shared/ui/chip";
import { Sheet } from "@/shared/ui/sheet";
import { ErrorState, Skeleton } from "@/shared/ui/states";
import { Thumb } from "@/shared/ui/thumb";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

import { feedKey, useItemActions } from "../feed/hooks";

import { useItemParam } from "./useItemParam";

function findInFeed(feed: Feed | null | undefined, ref: string): FeedItem | undefined {
  if (!feed) {
    return undefined;
  }
  return (
    [feed.hero, ...feed.rows.flatMap((row) => row.items)].find((item) => item?.ref === ref) ??
    undefined
  );
}

/** The item behind `?item=`, in a sheet: why it's here, where to find it, and more like it. */
export function ItemSheet({ profileId }: { profileId: string }) {
  const { openRef, open, close } = useItemParam();
  return (
    <Sheet open={openRef !== null} onOpenChange={(next) => !next && close()} title="Item details">
      {openRef && (
        <ItemDetailBody profileId={profileId} itemRef={openRef} onOpen={open} onClose={close} />
      )}
    </Sheet>
  );
}

interface BodyProps {
  profileId: string;
  itemRef: string;
  onOpen: (ref: string) => void;
  onClose: () => void;
}

function ItemDetailBody({ profileId, itemRef, onOpen, onClose }: BodyProps) {
  const queryClient = useQueryClient();
  const actions = useItemActions(profileId);
  const cached = findInFeed(queryClient.getQueryData<Feed | null>(feedKey(profileId)), itemRef);
  const detail = useQuery({
    queryKey: ["item", profileId, itemRef],
    queryFn: () => getItem(profileId, itemRef),
  });
  const preview = useMutation({ mutationFn: () => previewItem(profileId, itemRef) });

  const item: FeedItem | undefined = detail.data ?? cached;
  if (!item) {
    if (detail.isError) {
      return (
        <div className="p-6 pt-14">
          <ErrorState
            title="Can't open this one"
            error={detail.error}
            onRetry={() => void detail.refetch()}
          />
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-4 p-6 pt-14" aria-busy>
        <Skeleton className="aspect-[16/10] w-full" />
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    );
  }

  const type = item.entity_type as ItemType;
  const meta = TYPE_META[type];
  const [primary, ...others] = item.links;
  const liveItem = { ...item, ...(cached ? { liked: cached.liked, saved: cached.saved } : {}) };

  return (
    <article className="flex flex-col">
      <div className="relative">
        <Thumb
          src={item.image_url}
          title={item.title}
          type={type}
          aspect="wide"
          eager
          className="rounded-none md:rounded-t-2xl"
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-[linear-gradient(0deg,#ffffff_0%,#ffffff00_45%)]"
        />
      </div>

      <div className="-mt-10 flex flex-col gap-6 px-5 pb-8 md:px-7">
        <header className="relative flex flex-col gap-2">
          <div className="flex items-center gap-2.5">
            <TypeChip type={type} />
            {item.year && <span className="tabular text-sm text-muted">{item.year}</span>}
            <SourceBadge source={item.source} />
          </div>
          <h2 className="text-[30px] leading-[1.1] font-semibold">{item.title}</h2>
          {item.tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {item.tags.map((tag) => (
                <TagChip key={tag} className="h-7 text-[13px]">
                  {tag}
                </TagChip>
              ))}
            </div>
          )}
        </header>

        <section aria-labelledby="why-title" className="rounded-xl bg-surface-2 p-4">
          <h3 id="why-title" className="font-sans text-sm font-semibold tracking-normal text-muted">
            Why you're seeing this
          </h3>
          {item.because_of ? (
            <div className="mt-3 flex items-center gap-2.5 text-[15px]">
              <span className="max-w-[40%] truncate rounded-full bg-surface px-3 py-1.5 font-semibold text-ink shadow-soft">
                {item.because_of.title}
              </span>
              <span
                aria-hidden
                className="thread-segment h-[3px] min-w-6 flex-1 rounded-full"
                style={{
                  background: `linear-gradient(90deg, var(--ink), ${meta.color})`,
                  transformOrigin: "left",
                }}
              />
              <span
                className={cn(
                  "max-w-[40%] truncate rounded-full px-3 py-1.5 font-semibold",
                  meta.tint,
                  meta.text,
                )}
              >
                {item.title}
              </span>
            </div>
          ) : null}
          <p className="mt-3 text-[15px] text-body">
            {item.reason}
            {item.affinity !== null && item.affinity !== undefined && (
              <span className="text-muted"> Qloo match {Math.round(item.affinity * 100)}%.</span>
            )}
          </p>
        </section>

        <section aria-labelledby="where-title" className="flex flex-col gap-3">
          <h3 id="where-title" className="text-lg font-semibold">
            Where to find it
          </h3>
          {primary && (
            <Button asChild size="lg" className="w-full">
              <a
                href={primary.url}
                target="_blank"
                rel="noopener noreferrer"
                onClick={() => actions.opened(item, primary.platform)}
              >
                {primary.label} <ArrowUpRight />
              </a>
            </Button>
          )}
          {others.length > 0 && (
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {others.map((link) => (
                <li key={link.url}>
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={() => actions.opened(item, link.platform)}
                    className="flex h-11 items-center justify-between gap-2 rounded-lg border border-line px-3.5 text-[15px] font-medium text-ink transition-colors hover:border-[#c9c9c9] hover:bg-surface-2"
                  >
                    <span className="truncate">{link.label}</span>
                    <ArrowUpRight className="size-4 shrink-0 text-muted" />
                  </a>
                </li>
              ))}
            </ul>
          )}
          <p className="text-[13px] text-muted">
            “Search on” links search that service; “Open on” goes straight to the title.
          </p>
        </section>

        <div className="flex flex-wrap gap-2">
          <Button
            variant="secondary"
            onClick={() => void actions.toggleLike(liveItem)}
            aria-pressed={liveItem.liked}
          >
            <Heart className={cn(liveItem.liked && "fill-film text-film")} />{" "}
            {liveItem.liked ? "Liked" : "Like"}
          </Button>
          <Button
            variant="secondary"
            onClick={() => void actions.toggleSave(liveItem)}
            aria-pressed={liveItem.saved}
          >
            <Bookmark className={cn(liveItem.saved && "fill-primary text-primary-ink")} />{" "}
            {liveItem.saved ? "Saved" : "Save"}
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              void actions.notInterested(item);
              onClose();
            }}
          >
            <X /> Not for me
          </Button>
        </div>

        {detail.data?.preview_available && type !== "book" && (
          <section aria-label="Preview" className="flex flex-col gap-3">
            {preview.data ? (
              <div className="overflow-hidden rounded-xl bg-ink">
                <iframe
                  title={`Preview: ${preview.data.title}`}
                  src={`https://www.youtube-nocookie.com/embed/${preview.data.video_id}?rel=0`}
                  className="aspect-video w-full"
                  allow="encrypted-media; picture-in-picture"
                  allowFullScreen
                />
              </div>
            ) : (
              <Button variant="dark" onClick={() => preview.mutate()} disabled={preview.isPending}>
                <Play /> {preview.isPending ? "Finding a preview…" : "Preview on YouTube"}
              </Button>
            )}
            {preview.isError && (
              <p className="text-sm text-muted">No preview for this one right now.</p>
            )}
          </section>
        )}

        {detail.data && detail.data.more_like_this.length > 0 && (
          <section aria-labelledby="more-title" className="flex flex-col gap-3">
            <h3 id="more-title" className="text-lg font-semibold">
              More like this
            </h3>
            <ul className="no-scrollbar -mx-5 flex gap-3 overflow-x-auto px-5 md:-mx-7 md:px-7">
              {detail.data.more_like_this.map((more) => (
                <li key={more.ref} className="w-28 shrink-0">
                  <button
                    type="button"
                    onClick={() => onOpen(more.ref)}
                    className="flex w-full flex-col gap-1.5 text-left"
                  >
                    <Thumb
                      src={more.image_url}
                      title={more.title}
                      type={more.entity_type as ItemType}
                      aspect={more.entity_type === "artist" ? "square" : "poster"}
                    />
                    <span className="line-clamp-2 text-[13px] leading-snug font-semibold text-ink">
                      {more.title}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}
        {detail.isPending && <Skeleton className="h-40 w-full" />}
      </div>
    </article>
  );
}
