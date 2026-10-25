import { cn } from "cn";
import { Bookmark, Compass, Home, NotebookPen, Sparkles, type LucideIcon } from "lucide-react";
import { useRef } from "react";
import { NavLink, Outlet, useParams } from "react-router";

import { ItemSheet } from "../item-detail/ItemSheet";
import { RequireSession } from "../session/RequireSession";

import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

interface Tab {
  label: string;
  icon: LucideIcon;
  to: string;
  end?: boolean;
}

/** The signed-in frame: sidebar on desktop, top bar, the page, bottom tabs on phones, and the
 * item sheet any page can open with `?item=`. */
export function AppShell() {
  const { profileId = "" } = useParams();
  const searchRef = useRef<HTMLInputElement>(null);
  const base = `/p/${profileId}`;
  const tabs: Tab[] = [
    { label: "Home", icon: Home, to: base, end: true },
    { label: "Discover", icon: Compass, to: `${base}/discover` },
    { label: "Journal", icon: NotebookPen, to: `${base}/journal` },
    { label: "Saved", icon: Bookmark, to: `${base}/saved` },
    { label: "Taste", icon: Sparkles, to: `${base}/taste` },
  ];

  return (
    <RequireSession>
      <div className="flex min-h-dvh bg-surface">
        <Sidebar profileId={profileId} onAddTaste={() => searchRef.current?.focus()} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopBar profileId={profileId} searchRef={searchRef} />
          <main className="flex-1 px-4 pt-5 pb-28 md:px-6 lg:pb-10">
            <Outlet />
          </main>
        </div>
      </div>
      <nav
        aria-label="Main"
        className="fixed inset-x-0 bottom-0 z-30 border-t border-hairline bg-white/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-lg lg:hidden"
      >
        <ul className="grid grid-cols-5">
          {tabs.map((tab) => (
            <li key={tab.label}>
              <NavLink
                to={tab.to}
                end={tab.end}
                className={({ isActive }) =>
                  cn(
                    "flex h-16 flex-col items-center justify-center gap-1 text-xs font-semibold",
                    isActive ? "text-ink" : "text-muted",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <tab.icon className={cn("size-[22px]", isActive && "text-primary-ink")} />
                    {tab.label}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <ItemSheet profileId={profileId} />
    </RequireSession>
  );
}
