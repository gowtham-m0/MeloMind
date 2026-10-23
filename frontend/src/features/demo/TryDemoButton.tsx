import { Button } from "@/shared/ui/button";
import { ErrorBanner } from "@/shared/ui/states";

import { useTryDemo } from "./useTryDemo";

/** "Try the demo": a private, anonymous account with two sample profiles. No sign-up. */
export function TryDemoButton() {
  const tryDemo = useTryDemo();

  return (
    <div className="flex flex-col items-start gap-3">
      <Button size="lg" onClick={() => tryDemo.mutate()} disabled={tryDemo.isPending}>
        {tryDemo.isPending ? "Setting up the demo…" : "Try the demo"}
      </Button>
      {tryDemo.isError && <ErrorBanner error={tryDemo.error} title="The demo didn't start" />}
    </div>
  );
}
