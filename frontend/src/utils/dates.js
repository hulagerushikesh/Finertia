/**
 * Date helpers for the config panel's range.
 *
 * The native date picker shows dates in the browser's locale, so 06/01/2024
 * is 6 January to one tester and 1 June to the next (tester bug #2, 12 Oct).
 * Everything here works on the ISO string the API takes, and renders it with
 * a spelled-out month, which cannot be misread in any locale.
 *
 * Dates are parsed by hand rather than with `new Date("2024-01-06")`: that
 * form is read as UTC midnight, which is the previous evening west of
 * Greenwich, and the words would then name the wrong day.
 */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Mirrors backend/schemas.py so the estimate here matches the server's.
const TRADING_DAYS_PER_YEAR = 252;
const CALENDAR_DAYS_PER_YEAR = 365;

export const PRESETS = [
  { id: "1y", label: "1Y", years: 1 },
  { id: "3y", label: "3Y", years: 3 },
  { id: "5y", label: "5Y", years: 5 },
  { id: "10y", label: "10Y", years: 10 },
];

/** "2024-01-06" → { y: 2024, m: 1, d: 6 }, or null if it is not a real date. */
function parts(iso) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  if (!match) return null;
  const [y, m, d] = match.slice(1).map(Number);
  const probe = new Date(Date.UTC(y, m - 1, d));
  if (probe.getUTCMonth() !== m - 1 || probe.getUTCDate() !== d) return null;
  return { y, m, d };
}

/** Whole days since the epoch, timezone-free. */
function dayNumber(iso) {
  const p = parts(iso);
  return p ? Date.UTC(p.y, p.m - 1, p.d) / 86_400_000 : null;
}

const pad = (n) => String(n).padStart(2, "0");

/** Today in the user's own calendar, as YYYY-MM-DD. */
export function todayISO(now = new Date()) {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** "2024-01-06" → "6 Jan 2024". Returns "" for anything that is not a date. */
export function formatDay(iso) {
  const p = parts(iso);
  return p ? `${p.d} ${MONTHS[p.m - 1]} ${p.y}` : "";
}

/**
 * The last `years` years, ending today. 29 Feb steps back to 28 Feb in a
 * non-leap year rather than rolling over into March.
 */
export function presetRange(years, today = todayISO()) {
  const p = parts(today);
  const y = p.y - years;
  const leap = (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
  const d = p.m === 2 && p.d === 29 && !leap ? 28 : p.d;
  return { start: `${y}-${pad(p.m)}-${pad(d)}`, end: today };
}

/** The preset id a range matches exactly, or null. */
export function matchingPreset(start, end, today = todayISO()) {
  if (end !== today) return null;
  const hit = PRESETS.find((p) => presetRange(p.years, today).start === start);
  return hit ? hit.id : null;
}

/**
 * What the range means, in words, plus the first problem with it.
 *
 *   { words: "1 Jan 2024 → 6 Jan 2024", span: "5 days · ~3 trading days", problem: null }
 *
 * `problem` mirrors the server's own checks, so the panel can block the run
 * instead of sending a request that is bound to come back 422.
 */
export function describeRange(start, end, today = todayISO()) {
  const a = dayNumber(start);
  const b = dayNumber(end);
  if (a === null || b === null) {
    return { words: "", span: "", problem: "Pick both a start and an end date." };
  }

  const words = `${formatDay(start)} → ${formatDay(end)}`;
  if (a >= b) return { words, span: "", problem: "Start date must be before the end date." };
  if (b > dayNumber(today)) return { words, span: "", problem: "End date cannot be in the future." };

  const days = b - a;
  const trading = Math.floor((days * TRADING_DAYS_PER_YEAR) / CALENDAR_DAYS_PER_YEAR);
  const years = Math.round((days / CALENDAR_DAYS_PER_YEAR) * 10) / 10;
  const length =
    days >= CALENDAR_DAYS_PER_YEAR
      ? `${years} year${years === 1 ? "" : "s"}`
      : `${days} day${days === 1 ? "" : "s"}`;
  return { words, span: `${length} · ~${trading.toLocaleString("en-US")} trading days`, problem: null };
}
