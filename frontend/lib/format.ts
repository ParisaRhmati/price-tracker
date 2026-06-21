/**
 * Formatting helpers.
 *
 * Prices are displayed as-is in toman (both Digikala and Technolife now
 * report toman after backend normalisation). Dates are converted from the
 * server's Gregorian timestamps into the Jalali (Persian / Shamsi) calendar.
 *
 * If you ever switch the database back to storing rials, set
 * DISPLAY_DIVISOR to 10. For switching back to Gregorian, replace the
 * jalaali calls with new Date(...).toLocaleString calls.
 */

import jalaali from "jalaali-js";

const DISPLAY_DIVISOR = 1;

// --- Prices ------------------------------------------------------------

export function formatPrice(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(num)) return "—";
  return Math.round(num / DISPLAY_DIVISOR).toLocaleString("en-US");
}

export function formatPriceWithUnit(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${formatPrice(value)} T`;
}

export function formatDiff(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  const num = typeof value === "string" ? parseFloat(value) : value;
  if (Number.isNaN(num) || num === 0) return "0";
  const prefix = num > 0 ? "+" : "";
  return `${prefix}${Math.round(num / DISPLAY_DIVISOR).toLocaleString("en-US")}`;
}

// --- Dates / times -----------------------------------------------------

// Jalali month names. Used by formatDateTime when we want a friendly label.
const JALALI_MONTHS = [
  "Farvardin",
  "Ordibehesht",
  "Khordad",
  "Tir",
  "Mordad",
  "Shahrivar",
  "Mehr",
  "Aban",
  "Azar",
  "Dey",
  "Bahman",
  "Esfand",
];

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

/**
 * Convert a server-side ISO timestamp into a Jalali datetime string like
 *   "11 Khordad 1405 · 14:42"
 * Returns "—" for null / undefined / invalid input.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const { jy, jm, jd } = jalaali.toJalaali(date);
  const monthName = JALALI_MONTHS[jm - 1] ?? String(jm);
  return `${jd} ${monthName} ${jy} · ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * Short numeric Jalali form like "1405/03/11 14:42". Used in tables where
 * the friendly month name would be too long.
 */
export function formatDateTimeShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  const { jy, jm, jd } = jalaali.toJalaali(date);
  return `${jy}/${pad(jm)}/${pad(jd)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/**
 * "5m ago" / "2h ago" / "3d ago" — relative time relative to now. The
 * underlying arithmetic doesn't care about the calendar; only the
 * fallback (>60 days) does, and we switch to a Jalali short form there.
 */
export function formatRelativeTime(iso: string | null | undefined): string {
  if (!iso) return "never";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "never";
  const diffMs = Date.now() - date.getTime();
  const seconds = Math.round(diffMs / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 60) return `${days}d ago`;
  // After two months a relative phrase is more noisy than helpful.
  // Show the Jalali date instead.
  return formatDateTimeShort(iso);
}
