import { cn } from "cn";
import { ChevronDown, LogOut, Search, Settings, Users } from "lucide-react";
import { DropdownMenu } from "radix-ui";
import { useState, type RefObject } from "react";
import { useNavigate } from "react-router";

import { LogoMark } from "@/shared/ui/logo";

import { avatarColour, useProfile } from "../profiles/hooks";
import { useSignOut } from "../session/auth";

import { SearchBox } from "./SearchBox";

interface TopBarProps {
  profileId: string;
  searchRef: RefObject<HTMLInputElement | null>;
}

/** The sticky glass top bar: search and the profile menu. On phones, search opens below it. */
export function TopBar({ profileId, searchRef }: TopBarProps) {
  const profile = useProfile(profileId);
  const signOut = useSignOut();
  const navigate = useNavigate();
  const [searchOpen, setSearchOpen] = useState(false);
  const name = profile.data?.display_name ?? "";

  return (
    <header className="sticky top-0 z-20 border-b border-hairline bg-white/85 backdrop-blur-lg">
      <div className="flex h-16 items-center gap-3 px-4 md:px-6">
        <span className="lg:hidden">
          <LogoMark />
        </span>
        <SearchBox
          ref={searchRef}
          profileId={profileId}
          className="hidden max-w-[560px] flex-1 md:block"
        />
        <div className="flex-1 md:hidden" />
        <button
          type="button"
          className="grid size-11 place-items-center rounded-full text-ink hover:bg-surface-2 md:hidden"
          aria-label="Search"
          aria-expanded={searchOpen}
          onClick={() => setSearchOpen((open) => !open)}
        >
          <Search className="size-5" />
        </button>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger className="flex h-11 items-center gap-2.5 rounded-full py-1 pr-2 pl-1 transition-colors hover:bg-surface-2 md:ml-auto">
            <span
              className={cn(
                "grid size-9 place-items-center rounded-full font-display text-base font-semibold text-ink",
                avatarColour(profileId),
              )}
            >
              {name.slice(0, 1).toUpperCase()}
            </span>
            <span className="hidden text-[15px] font-semibold text-ink sm:inline">
              {name ? `Hey, ${name}` : "Hey there"}
            </span>
            <ChevronDown className="size-4 text-muted" />
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={8}
              className="rise-in z-50 min-w-52 rounded-xl border border-hairline bg-surface p-1.5 shadow-lift"
            >
              <DropdownMenu.Item
                onSelect={() => void navigate(`/p/${profileId}/settings`)}
                className="flex h-11 cursor-pointer items-center gap-3 rounded-lg px-3 text-[15px] text-ink outline-none data-highlighted:bg-surface-2"
              >
                <Settings className="size-4 text-muted" /> Settings
              </DropdownMenu.Item>
              <DropdownMenu.Item
                onSelect={() => void navigate("/profiles")}
                className="flex h-11 cursor-pointer items-center gap-3 rounded-lg px-3 text-[15px] text-ink outline-none data-highlighted:bg-surface-2"
              >
                <Users className="size-4 text-muted" /> Switch profile
              </DropdownMenu.Item>
              <DropdownMenu.Item
                onSelect={() => signOut.mutate()}
                className="flex h-11 cursor-pointer items-center gap-3 rounded-lg px-3 text-[15px] text-ink outline-none data-highlighted:bg-surface-2"
              >
                <LogOut className="size-4 text-muted" /> Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
      {searchOpen && (
        <div className="px-4 pb-3 md:hidden">
          <SearchBox profileId={profileId} />
        </div>
      )}
    </header>
  );
}
