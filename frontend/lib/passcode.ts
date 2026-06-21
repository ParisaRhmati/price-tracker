/**
 * Passcode storage helper.
 *
 * Stores the verified passcode in localStorage with a 30-day expiry, so a
 * user typing the code on Monday doesn't need to retype it the next morning.
 * Used by both the gate component (writes after a successful /api/auth/check/)
 * and the api client (reads to attach the X-App-Passcode header).
 *
 * SSR-safe: every read/write is guarded by a `typeof window` check, because
 * Next.js will import this module during server rendering where `window`
 * doesn't exist.
 */

const STORAGE_KEY = "price-tracker:passcode";
const EXPIRY_MS = 30 * 24 * 60 * 60 * 1000; // 30 days

interface StoredPasscode {
  code: string;
  savedAt: number;
}

export function readStoredPasscode(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const data = JSON.parse(raw) as StoredPasscode;
    if (!data?.code || typeof data.savedAt !== "number") return null;
    if (Date.now() - data.savedAt > EXPIRY_MS) {
      window.localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return data.code;
  } catch {
    return null;
  }
}

export function writeStoredPasscode(code: string): void {
  if (typeof window === "undefined") return;
  const data: StoredPasscode = { code, savedAt: Date.now() };
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

export function clearStoredPasscode(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
