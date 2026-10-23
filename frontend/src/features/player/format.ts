/** "3:05": minutes and seconds, for a progress readout. */
export function formatClock(seconds: number): string {
  const whole = Math.max(Math.floor(seconds), 0);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

/** "18 min 20 s", or "45 s" under a minute. */
export function formatLength(seconds: number): string {
  const whole = Math.max(Math.round(seconds), 0);
  const minutes = Math.floor(whole / 60);
  const rest = whole % 60;
  if (minutes === 0) {
    return `${rest} s`;
  }
  return rest === 0 ? `${minutes} min` : `${minutes} min ${rest} s`;
}
