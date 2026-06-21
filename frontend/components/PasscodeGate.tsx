"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Lock } from "lucide-react";

import { api } from "@/lib/api";
import {
  readStoredPasscode,
  writeStoredPasscode,
} from "@/lib/passcode";

/**
 * Full-screen gate that asks the visitor for the app's shared passcode
 * before the rest of the UI mounts.
 *
 * Mount strategy:
 *   - On first render we don't know yet whether the user is authorised.
 *     We return null briefly while we check localStorage and verify the
 *     stored code (if any) with the backend.
 *   - If the backend says the passcode feature is disabled (empty
 *     APP_PASSCODE), we skip the gate entirely.
 *   - On a valid code we render `children` (the real app).
 *
 * The verification call is the same /api/auth/check/ endpoint the gate
 * uses to validate new submissions, so a code revoked server-side is
 * detected on the very next page load.
 */
export default function PasscodeGate({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<
    "checking" | "needs-code" | "verifying" | "ok"
  >("checking");
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState("");

  // Initial mount: try the stored code (if any) and decide whether to
  // show the prompt or unlock straight away.
  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      const stored = readStoredPasscode();
      try {
        if (!stored) {
          // Still hit /auth/check/ with an empty value so we can detect
          // the "passcode feature disabled" case.
          const res = await api.verifyPasscode("");
          if (cancelled) return;
          if (res.disabled) {
            setStatus("ok"); // gate not needed
          } else {
            setStatus("needs-code");
          }
          return;
        }
        const res = await api.verifyPasscode(stored);
        if (cancelled) return;
        if (res.ok) {
          setStatus("ok");
        } else {
          setStatus("needs-code");
        }
      } catch {
        if (cancelled) return;
        // Backend unreachable - we can't be sure either way. Show the
        // gate so the user gets a clear message instead of a half-loaded
        // app.
        setStatus("needs-code");
        setError("Couldn't reach the server. Try again in a moment.");
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const code = input.trim();
    if (!code) {
      setError("Please enter the passcode.");
      return;
    }
    setStatus("verifying");
    setError(null);
    try {
      const res = await api.verifyPasscode(code);
      if (res.ok) {
        writeStoredPasscode(code);
        setStatus("ok");
      } else {
        setStatus("needs-code");
        setError("That passcode doesn't match. Try again.");
      }
    } catch {
      setStatus("needs-code");
      setError("Couldn't reach the server. Try again in a moment.");
    }
  }

  if (status === "ok") {
    return <>{children}</>;
  }

  // While we're checking the stored code we don't show the form yet -
  // a half-flash of the prompt is worse than a brief blank screen.
  if (status === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-50">
        <p className="text-sm text-ink-500">Loading…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-ink-50 px-6">
      <div className="w-full max-w-sm rounded-2xl border border-ink-200 bg-white p-8 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-ink-900 text-ink-50">
            <Lock className="h-5 w-5" strokeWidth={1.8} />
          </span>
          <div>
            <h1 className="font-display text-2xl text-ink-900">
              Price Tracker
            </h1>
            <p className="text-xs text-ink-500">Enter the shared passcode</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-xs uppercase tracking-[0.18em] text-ink-500">
              Passcode
            </span>
            <input
              type="password"
              autoFocus
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="w-full rounded-lg border border-ink-200 bg-white px-3 py-2.5 text-base outline-none transition focus:border-ink-900 focus:ring-2 focus:ring-ink-900/10"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>

          {error && (
            <p className="rounded-md bg-bad-soft px-3 py-2 text-xs text-bad ring-1 ring-inset ring-red-200">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={status === "verifying"}
            className="inline-flex w-full items-center justify-center rounded-lg bg-ink-900 px-4 py-2.5 text-sm font-medium text-ink-50 transition hover:bg-ink-700 disabled:opacity-50"
          >
            {status === "verifying" ? "Checking…" : "Unlock"}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-ink-400">
          Ask the app owner for the passcode.
        </p>
      </div>
    </div>
  );
}
