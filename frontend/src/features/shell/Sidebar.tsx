import { cn } from "cn";
import {
  BookOpen,
  Bookmark,
  Clapperboard,
  Compass,
  Home,
  HelpCircle,
  Music2,
  NotebookPen,
  Settings,
  Sparkles,
  Users,
  type LucideIcon,
} from "lucide-react";
import { NavLink } from "react-router";

import { TagChip } from "@/shared/ui/chip";
import { Logo } from "@/shared/ui/logo";

import { useFeedSnapshot } from "../feed/hooks";

interface NavItem {
  label: string;
  icon: LucideIcon;
  to?: string;
  end?: boolean;
}

function navItems(base: string): NavItem[] {
  return [
    { label: "Home", icon: Home, to: base, end: true },
    { label: "Discover", icon: Compass, to: `${base}/discover`, end: true },
    { label: "Music", icon: Music2, to: `${base}/discover/artist` },
    { label: "Movies & TV", icon: Clapperboard, to: `${base}/discover/movie` },
    { label: "Books", icon: BookOpen, to: `${base}/discover/book` },
    { label: "Saved", icon: Bookmark, to: `${base}/saved` },
    { label: "Journal", icon: NotebookPen, to: `${base}/journal` },
    { label: "Taste", icon: Sparkles, to: `${base}/taste`, end: true },
    { label: "Taste match", icon: Users, to: `${base}/taste/match` },
    { label: "Settings", icon: Settings, to: `${base}/settings` },
    { label: "How it works", icon: HelpCircle, to: "/how-it-works" },
  ];
}

/** The desktop sidebar: brand, navigation, and the taste the agent has picked up so far. */
export function Sidebar({ profileId, onAddTaste }: { profileId: string; onAddTaste: () => void }) {
  const feed = useFeedSnapshot(profileId);
  const tags = feed.data?.taste_tags ?? [];

  return (
    <aside className="no-scrollbar sticky top-0 hidden h-dvh w-[248px] shrink-0 flex-col gap-7 overflow-y-auto border-r border-hairline bg-surface px-4 py-6 lg:flex">
      <div className="px-2">
        <Logo withTagline />
      </div>

      <nav aria-label="Main">
        <ul className="flex flex-col gap-0.5">
          {navItems(`/p/${profileId}`).map((item) => (
            <li key={item.label}>
              {item.to ? (
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    cn(
                      "flex h-11 items-center gap-3 rounded-[10px] px-3 text-[15px] font-medium transition-colors",
                      isActive
                        ? "bg-primary-tint text-ink"
                        : "text-body hover:bg-surface-2 hover:text-ink",
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <item.icon
                        className={cn("size-[19px]", isActive ? "text-primary-ink" : "text-muted")}
                      />
                      {item.label}
                    </>
                  )}
                </NavLink>
              ) : (
                <span className="flex h-11 items-center gap-3 rounded-[10px] px-3 text-[15px] font-medium text-muted">
                  <item.icon className="size-[19px]" />
                  {item.label}
                  <span className="ml-auto rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold">
                    Soon
                  </span>
                </span>
              )}
            </li>
          ))}
        </ul>
      </nav>

      <section aria-labelledby="taste-profile-title" className="px-2">
        <h2
          id="taste-profile-title"
          className="font-sans text-sm font-semibold tracking-normal text-ink"
        >
          Your taste profile
        </h2>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {tags.length === 0 && (
            <p className="text-sm text-muted">Shows up after your first feed.</p>
          )}
          {tags.map((tag) => (
            <TagChip key={tag} className="h-7 text-[13px]">
              {tag}
            </TagChip>
          ))}
          <button
            type="button"
            onClick={onAddTaste}
            className="inline-flex h-7 items-center rounded-full px-2.5 text-[13px] font-semibold text-primary-ink transition-colors hover:bg-primary-tint"
          >
            + Add more
          </button>
        </div>
      </section>

      <p className="mt-auto rounded-xl bg-surface-2 p-4 text-sm text-body">
        <span className="font-semibold text-ink">Every like teaches the agent.</span> Heart a few
        things and refresh to watch your feed shift.
      </p>
    </aside>
  );
}
