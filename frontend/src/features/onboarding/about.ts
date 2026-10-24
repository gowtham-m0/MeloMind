export const MIN_BIRTH_YEAR = 1900;

/** The country and birth year, both optional. */
export interface About {
  country: string;
  birthYear: string;
}

/** The birth year as a number, or null when it's blank or out of range. */
export function parseBirthYear(value: string): number | null {
  const year = Number(value);
  const valid =
    Number.isInteger(year) && year >= MIN_BIRTH_YEAR && year <= new Date().getFullYear();
  return value.trim() && valid ? year : null;
}
