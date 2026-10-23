// Full class names, so Tailwind can see them. The colours are tokens in index.css.
const DECADE_CLASSES: Record<number, string> = {
  1940: "bg-decade-1940s",
  1950: "bg-decade-1950s",
  1960: "bg-decade-1960s",
  1970: "bg-decade-1970s",
  1980: "bg-decade-1980s",
};

/** The decade a year falls in: 1964 → 1960. */
export function decadeOf(year: number | null | undefined): number | null {
  return year == null ? null : Math.floor(year / 10) * 10;
}

/** The background class for a decade's colour, with a neutral one for others or unknown. */
export function decadeClass(decade: number | null | undefined): string {
  return (decade != null && DECADE_CLASSES[decade]) || "bg-decade-other";
}

/** "1960s", or null when the decade is unknown. */
export function decadeLabel(decade: number | null | undefined): string | null {
  return decade == null ? null : `${decade}s`;
}
