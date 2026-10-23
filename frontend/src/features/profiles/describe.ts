/** "Born 1948 · grew up in Chicago, United States", leaving out anything not known. */
export function describeProfile(
  birthYear: number,
  placesLived: string[],
  country: string | null,
): string {
  const where = [placesLived[0], country].filter(Boolean).join(", ");
  return where ? `Born ${birthYear} · grew up in ${where}` : `Born ${birthYear}`;
}

/** The places lived with the hometown (always the first place) replaced or removed. */
export function withHometown(placesLived: string[], town: string): string[] {
  const rest = placesLived.slice(1);
  const trimmed = town.trim();
  return trimmed ? [trimmed, ...rest] : rest;
}
