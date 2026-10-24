import type { AgentRun } from "@/shared/api/feed";
import { LogoMark } from "@/shared/ui/logo";
import { Skeleton } from "@/shared/ui/states";

import { AgentLog } from "./AgentLog";

/** The first build: skeleton rows on one side, the agent narrating its work on the other. */
export function FeedBuilding({ name, run }: { name: string; run: AgentRun | null }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]" aria-busy>
      <div className="flex flex-col gap-6">
        <div className="relative overflow-hidden rounded-2xl bg-ink p-6 text-white md:p-10">
          <LogoMark onDark className="size-10 animate-pulse" />
          <h1 className="mt-5 text-[32px] leading-tight font-semibold text-white md:text-[40px]">
            Building <span className="text-primary">your</span> feed, {name}
          </h1>
          <p className="mt-2 max-w-[48ch] text-white/75">
            The agent is asking Qloo for music, films, shows and books that match your taste. This
            takes about half a minute.
          </p>
        </div>
        {[0, 1].map((row) => (
          <div key={row} className="flex flex-col gap-3">
            <Skeleton className="h-6 w-56" />
            <div className="flex gap-3.5 overflow-hidden">
              {[0, 1, 2, 3, 4, 5].map((card) => (
                <Skeleton
                  key={card}
                  className="aspect-[3/4] w-[calc((100%-2*14px)/2.3)] shrink-0 sm:w-[calc((100%-4*14px)/4.5)] xl:w-[calc((100%-6*14px)/6.5)]"
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      <aside className="rounded-xl border border-hairline bg-surface p-4 shadow-soft">
        <h2 className="mb-3 text-lg font-semibold">What the agent is doing</h2>
        <AgentLog run={run} compact />
      </aside>
    </div>
  );
}
