import { Heart, Plus } from "lucide-react";
import { useState, type ReactNode } from "react";

import { Button } from "@/shared/ui/button";
import { SourceBadge, TagChip, ToggleChip, TypeChip } from "@/shared/ui/chip";
import { Logo, LogoMark } from "@/shared/ui/logo";
import { Sheet } from "@/shared/ui/sheet";
import { EmptyState, ErrorState, Skeleton } from "@/shared/ui/states";
import { Thumb } from "@/shared/ui/thumb";
import { useToast } from "@/shared/ui/toast";
import { TYPE_META, type ItemType } from "@/shared/ui/types";

const TOKENS = [
  ["ink", "bg-ink"],
  ["body", "bg-body"],
  ["muted", "bg-muted"],
  ["surface", "bg-surface"],
  ["surface-2", "bg-surface-2"],
  ["line", "bg-line"],
  ["primary", "bg-primary"],
  ["brand", "bg-brand"],
  ["music", "bg-music"],
  ["film", "bg-film"],
  ["tv", "bg-tv"],
  ["book", "bg-book"],
  ["danger", "bg-danger"],
] as const;

const TYPES = Object.keys(TYPE_META) as ItemType[];
const MOODS = ["Chill", "Happy", "Focused", "Melancholy", "Energetic"];

/**
 * Every shared component on one page, for design review. Images are the fallback tiles only:
 * we never store or re-host pictures (rule 13), and real ones come from Qloo in the feed.
 */
export function StyleguidePage() {
  const toast = useToast();
  const [mood, setMood] = useState("Chill");
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-surface">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-5 py-5 md:px-8">
        <Logo withTagline />
        <span className="text-sm text-muted">Styleguide</span>
      </header>
      <main className="mx-auto flex max-w-5xl flex-col gap-14 px-5 pt-6 pb-20 md:px-8">
        <div>
          <h1 className="text-[40px] leading-tight font-semibold md:text-[52px]">
            The <span className="text-primary">pieces</span>
          </h1>
          <p className="mt-2 max-w-[60ch] text-lg text-body">
            Tokens and shared components from <code>src/shared/ui</code>. Features build only from
            these.
          </p>
        </div>

        <Section title="Colour tokens">
          <ul className="grid grid-cols-3 gap-3 sm:grid-cols-5 md:grid-cols-7">
            {TOKENS.map(([name, swatch]) => (
              <li key={name} className="flex flex-col gap-1.5">
                <span className={`h-14 rounded-[10px] border border-hairline ${swatch}`} />
                <span className="text-sm text-body">{name}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Type">
          <p className="font-display text-[44px] leading-tight font-semibold text-ink">
            Chillax for titles
          </p>
          <p className="text-lg text-body">
            Switzer for everything else: body text at 16 px and up, secondary text in muted.
          </p>
          <p className="text-muted">Muted secondary line.</p>
        </Section>

        <Section title="Buttons">
          <div className="flex flex-wrap items-center gap-3">
            <Button>Primary</Button>
            <Button variant="secondary">Secondary</Button>
            <Button variant="ghost">Ghost</Button>
            <Button variant="dark">Dark</Button>
            <Button disabled>Disabled</Button>
            <Button size="sm" variant="secondary">
              Small
            </Button>
            <Button size="icon" variant="secondary" aria-label="Like">
              <Heart />
            </Button>
          </div>
          <div className="flex flex-wrap gap-3 rounded-2xl bg-ink p-5">
            <Button variant="onImage">On an image</Button>
            <Button>
              <Plus /> With an icon
            </Button>
          </div>
        </Section>

        <Section title="Chips and badges">
          <div className="flex flex-wrap gap-2">
            {TYPES.map((type) => (
              <TypeChip key={type} type={type} />
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {["Indie", "Sci fi", "Coming of age", "Dream pop"].map((tag) => (
              <TagChip key={tag}>{tag}</TagChip>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            {MOODS.map((name) => (
              <ToggleChip key={name} selected={mood === name} onClick={() => setMood(name)}>
                {name}
              </ToggleChip>
            ))}
          </div>
          <div className="flex flex-wrap gap-2">
            <SourceBadge source="qloo_live" />
            <SourceBadge source="demo_fixture" />
            <SourceBadge source="song_catalogue" />
          </div>
        </Section>

        <Section title="Fallback tiles">
          <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-5">
            {TYPES.map((type) => (
              <li key={type}>
                <Thumb
                  src={null}
                  title={`${TYPE_META[type].label} with no image`}
                  type={type}
                  aspect={type === "artist" || type === "song" ? "square" : "poster"}
                  round={type === "artist"}
                  className="w-full"
                />
              </li>
            ))}
          </ul>
        </Section>

        <Section title="States">
          <div className="flex gap-3">
            <Skeleton className="aspect-[2/3] w-28" />
            <Skeleton className="aspect-[2/3] w-28" />
            <Skeleton className="aspect-[2/3] w-28" />
          </div>
          <EmptyState
            title="Nothing saved yet"
            action={<Button variant="secondary">Browse your feed</Button>}
          >
            Tap the bookmark on any card and it lands here.
          </EmptyState>
          <ErrorState
            error={new Error("Qloo didn't answer in time.")}
            onRetry={() => toast.show("Retried.")}
          />
        </Section>

        <Section title="Toast and sheet">
          <div className="flex flex-wrap gap-3">
            <Button variant="secondary" onClick={() => toast.show("Saved to your list.")}>
              Show a toast
            </Button>
            <Button
              variant="secondary"
              onClick={() => toast.show("Hidden from your feed.", () => toast.show("Undone."))}
            >
              Toast with Undo
            </Button>
            <Button variant="secondary" onClick={() => setSheetOpen(true)}>
              Open the sheet
            </Button>
          </div>
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen} title="Example sheet">
            <div className="flex flex-col gap-3 p-6">
              <LogoMark />
              <h2 className="text-[26px] font-semibold">A detail sheet</h2>
              <p className="text-body">
                A bottom sheet on phones and a drawer from 768 px. Escape or the overlay closes it.
              </p>
            </div>
          </Sheet>
        </Section>
      </main>
    </div>
  );
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-4">
      <h2 className="text-[24px] font-semibold">{title}</h2>
      {children}
    </section>
  );
}
