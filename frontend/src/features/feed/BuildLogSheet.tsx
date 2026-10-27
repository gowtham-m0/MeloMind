import { useQuery } from "@tanstack/react-query";

import { getRun, type AgentRun } from "@/shared/api/feed";
import { Sheet } from "@/shared/ui/sheet";
import { Skeleton } from "@/shared/ui/states";

import { AgentLog } from "./AgentLog";

interface BuildLogSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runId: string;
  liveRun: AgentRun | null;
  title?: string;
}

/** "How this feed was built": every step the agent took, in plain English. */
export function BuildLogSheet({
  open,
  onOpenChange,
  runId,
  liveRun,
  title = "How this feed was built",
}: BuildLogSheetProps) {
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => getRun(runId),
    enabled: open && liveRun?.id !== runId,
  });
  const shown = liveRun?.id === runId ? liveRun : (run.data ?? null);

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={title}>
      <div className="flex flex-col gap-5 p-6 pt-8 md:p-8">
        <div>
          <h2 className="text-[26px] leading-tight font-semibold">{title}</h2>
          <p className="mt-1 text-body">
            Every pick comes from Qloo. The agent chose what to ask for; code ranked the results,
            kept out anything you're not into, and checked the rules.
          </p>
        </div>
        {shown ? <AgentLog run={shown} /> : <Skeleton className="h-64 w-full" />}
      </div>
    </Sheet>
  );
}
