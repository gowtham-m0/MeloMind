import { useMutation } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { quizNext, type FeedItem, type QuizStep } from "@/shared/api/feed";
import { Button } from "@/shared/ui/button";
import { TypeChip } from "@/shared/ui/chip";
import { ErrorState } from "@/shared/ui/states";
import { Thumb } from "@/shared/ui/thumb";
import type { ItemType } from "@/shared/ui/types";

interface StepQuizProps {
  profileId: string;
  onDone: () => void;
}

/**
 * Step 4: "this or that". Two big cards at a time; the tap is a taste signal, the card you
 * leave behind gets nothing. The server picks each next pair to follow your last choice.
 */
export function StepQuiz({ profileId, onDone }: StepQuizProps) {
  const [step, setStep] = useState<QuizStep | null>(null);
  const shown = useRef<string[]>([]);
  const mutation = useMutation({
    mutationFn: (pickedRef?: string) => quizNext(profileId, shown.current, pickedRef),
    onSuccess: (next) => {
      if (next.done || !next.pair) {
        onDone();
        return;
      }
      shown.current = [...shown.current, ...next.pair.map((item) => item.ref)];
      setStep(next);
    },
  });
  const { mutate } = mutation;

  useEffect(() => {
    mutate(undefined);
    // The quiz starts once, when the step mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (mutation.isError && !step) {
    return (
      <ErrorState
        title="The quiz didn't load"
        error={mutation.error}
        onRetry={() => mutate(undefined)}
      />
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-[36px] leading-tight font-semibold md:text-[44px]">
          This <span className="text-primary">or</span> that?
        </h1>
        <p className="mt-2 max-w-[52ch] text-lg text-body">
          Tap the one you'd rather watch, hear or read. Go with your gut.
          {step && (
            <span className="tabular ml-2 whitespace-nowrap text-muted">
              {step.round} of {step.rounds}
            </span>
          )}
        </p>
      </div>

      {/* Width follows the viewport height, so both 4:5 cards and their titles fit on screen. */}
      <div
        aria-live="polite"
        className="mx-auto grid w-full max-w-[max(28rem,calc((100dvh-21rem)*1.6))] grid-cols-2 gap-4 md:gap-6"
      >
        {step?.pair
          ? step.pair.map((item) => (
              <QuizCard
                key={`${step.round}-${item.ref}`}
                item={item}
                disabled={mutation.isPending}
                onPick={() => mutate(item.ref)}
              />
            ))
          : [0, 1].map((slot) => (
              <div key={slot} className="aspect-[4/5] animate-pulse rounded-2xl bg-surface-2" />
            ))}
      </div>
      {mutation.isError && (
        <p role="alert" className="text-danger">
          That pick didn't save. Tap a card to try again.
        </p>
      )}

      <div className="flex justify-end">
        <Button variant="ghost" onClick={onDone}>
          Skip the quiz
        </Button>
      </div>
    </div>
  );
}

function QuizCard({
  item,
  disabled,
  onPick,
}: {
  item: FeedItem;
  disabled: boolean;
  onPick: () => void;
}) {
  const type = item.entity_type as ItemType;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onPick}
      className="rise-in lift flex flex-col gap-3 rounded-2xl text-left disabled:opacity-60"
    >
      <Thumb
        src={item.image_url}
        title={item.title}
        type={type}
        aspect="poster"
        eager
        className="aspect-[4/5] w-full rounded-2xl"
      />
      <span className="flex flex-col gap-0.5 px-1">
        <span className="flex items-center gap-2">
          <TypeChip type={type} />
          {item.year && <span className="tabular text-xs text-muted">{item.year}</span>}
        </span>
        <span className="line-clamp-2 text-lg leading-snug font-semibold text-ink">
          {item.title}
        </span>
        <span className="line-clamp-2 text-sm leading-snug text-muted">{item.reason}</span>
      </span>
    </button>
  );
}
