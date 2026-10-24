import { useCallback } from "react";
import { useSearchParams } from "react-router";

const PARAM = "item";

/** The open item lives in the URL (`?item=<ref>`), so Back closes the sheet and links share it. */
export function useItemParam() {
  const [params, setParams] = useSearchParams();
  const openRef = params.get(PARAM);

  const open = useCallback(
    (ref: string) => {
      setParams((current) => {
        const next = new URLSearchParams(current);
        next.set(PARAM, ref);
        return next;
      });
    },
    [setParams],
  );

  const close = useCallback(() => {
    setParams((current) => {
      const next = new URLSearchParams(current);
      next.delete(PARAM);
      return next;
    });
  }, [setParams]);

  return { openRef, open, close };
}
