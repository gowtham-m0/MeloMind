export const BIRTH_YEAR_MIN = 1920;
export const BIRTH_YEAR_MAX = 1990;

/** Errors for the two required fields, keyed by field. Empty when both are fine. */
export interface BasicsErrors {
  displayName?: string;
  birthYear?: string;
}

/** Checks the name and birth year the way the backend will. */
export function validateBasics(displayName: string, birthYear: string): BasicsErrors {
  const errors: BasicsErrors = {};
  if (!displayName.trim()) {
    errors.displayName = "Add the name you call them by.";
  } else if (displayName.trim().length > 60) {
    errors.displayName = "Keep the name under 60 characters.";
  }
  const year = Number(birthYear);
  if (!birthYear.trim()) {
    errors.birthYear = "Add the year they were born.";
  } else if (!Number.isInteger(year) || year < BIRTH_YEAR_MIN || year > BIRTH_YEAR_MAX) {
    errors.birthYear = `Use a year between ${BIRTH_YEAR_MIN} and ${BIRTH_YEAR_MAX}.`;
  }
  return errors;
}
