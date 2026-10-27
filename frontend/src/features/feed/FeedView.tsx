import { cn } from "cn";
import { useState } from "react";
import { useNavigate } from "react-router";

import type { FeedItem, FeedRow } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { EmptyState, ErrorState } from "@/shared/ui/states";

import { AskRow } from "../ask/AskRow";
import { useAsk } from "../ask/useAsk";
import { useItemParam } from "../item-detail/useItemParam";
import { useProfile } from "../profiles/hooks";

import { BuildLogSheet } from "./BuildLogSheet";
import { CategoryTiles } from "./CategoryTiles";
import { FeedBuilding } from "./FeedBuilding";
import { FeedRowView } from "./FeedRowView";
import { FeedStatusBar } from "./FeedStatusBar";
import { HeroBanner } from "./HeroBanner";
import { useFeed, useItemActions } from "./hooks";
import { QuickActions, VibePanel } from "./RailPanels";
import { TasteThread } from "./TasteThread";
import { WelcomeTip } from "./WelcomeTip";

/** Where each row's "See all" lands in Discover: a type group, narrowed to a kind. */
const SEE_ALL: Record<string, string> = {
  music: "artist?only=artist",
  songs: "artist?only=song",
  films: "movie?only=movie",
  tv: "movie?only=tv_show",
  books: "book",
};

/** The home screen: status line, hero, category tiles and rows, with the right rail beside them
 * on wide screens and below them on narrow ones. */
export function FeedView({ profileId }: { profileId: string }) {
  const { feed, run, building, buildFailed, buildError, refresh } = useFeed(profileId);
  const actions = useItemActions(profileId);
  const navigate = useNavigate();
  const { open } = useItemParam();
  const profile = useProfile(profileId);
  const [logOpen, setLogOpen] = useState(false);
  const asking = useAsk();

  if (feed.isError) {
    return <ErrorState error={feed.error} onRetry={() => void feed.refetch()} />;
  }
  if (!feed.data) {
    if (buildFailed) {
      return (
        <ErrorState
          title="The agent couldn't build your feed"
          error={buildError ?? new Error("Add a few favourites with search, then try again.")}
          onRetry={refresh}
        />
      );
    }
    return <FeedBuilding name={profile.data?.display_name ?? "friend"} run={run} />;
  }

  const data = feed.data;
  if (!data.hero && data.rows.length === 0) {
    return (
      <EmptyState
        title="Nothing to show yet"
        action={
          <Button onClick={refresh} disabled={building}>
            {building ? "The agent is working…" : "Build my feed again"}
          </Button>
        }
      >
        Every pick was hidden, or Qloo had nothing new for you. Add a few more favourites with the
        search bar, or bring back anything you hid in Settings, then build again.
      </EmptyState>
    );
  }
  const rail = data.rows.find((row) => row.placement === "rail");
  const rows = data.rows.filter((row) => row.placement === "main");
  const openItem = (item: FeedItem) => open(item.ref);
  const cardActions = {
    onOpen: openItem,
    onLike: (item: FeedItem) => void actions.toggleLike(item),
    onSave: (item: FeedItem) => void actions.toggleSave(item),
    onDismiss: (item: FeedItem) => void actions.notInterested(item),
    onOpened: actions.opened,
  };
  const jump = (key: string) => {
    const target = document.getElementById(`row-${key}`);
    if (target) {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    } else if (SEE_ALL[key]) {
      void navigate(`/p/${profileId}/discover/${SEE_ALL[key]}`);
    }
  };
  const seeAll = (row: FeedRow) =>
    SEE_ALL[row.key] ? `/p/${profileId}/discover/${SEE_ALL[row.key]}` : undefined;

  return (
    <div className="grid gap-x-6 gap-y-7 xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex min-w-0 flex-col gap-7 xl:col-start-1 xl:row-start-1">
        <FeedStatusBar
          feed={data}
          building={building}
          run={run}
          onRefresh={refresh}
          onShowLog={() => setLogOpen(true)}
        />
        {data.hero && (
          <HeroBanner
            item={data.hero}
            onWhy={openItem}
            onLike={cardActions.onLike}
            onOpened={actions.opened}
          />
        )}
        <WelcomeTip profileId={profileId} onAsk={asking.openComposer} />
        <AskRow {...cardActions} />
        <CategoryTiles feed={data} profileId={profileId} />
        {rail && (
          <div className="xl:hidden">
            <TasteThread row={rail} onOpen={openItem} />
          </div>
        )}
      </div>

      <aside
        aria-label="For you right now"
        className="flex flex-col gap-4 xl:col-start-2 xl:row-span-2 xl:row-start-1 xl:self-start"
      >
        {rail && (
          <div className="hidden xl:block">
            <TasteThread row={rail} onOpen={openItem} />
          </div>
        )}
        <QuickActions
          onJump={jump}
          onRefresh={refresh}
          onJournal={() => void navigate(`/p/${profileId}/journal?compose`)}
          onSurprise={() => asking.ask({ kind: "surprise" }, "A surprise")}
        />
        <VibePanel busy={asking.running} onGo={(mood, label) => asking.ask({ mood }, label)} />
      </aside>

      <div
        className={cn(
          "flex min-w-0 flex-col gap-9 transition-opacity duration-200 xl:col-start-1 xl:row-start-2",
          building && "opacity-60",
        )}
      >
        {rows.map((row) => (
          <FeedRowView key={row.key} row={row} seeAll={seeAll(row)} {...cardActions} />
        ))}
      </div>

      <BuildLogSheet
        open={logOpen}
        onOpenChange={setLogOpen}
        runId={run?.id ?? data.agent_run_id}
        liveRun={run}
      />
    </div>
  );
}
