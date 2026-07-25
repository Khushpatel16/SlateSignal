"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";

const CONSENT_KEY = "slatesignal-cookie-consent";

export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const hasConsent = Boolean(window.localStorage.getItem(CONSENT_KEY));
    queueMicrotask(() => setVisible(!hasConsent));
  }, []);

  function choose(value: "essential" | "analytics") {
    window.localStorage.setItem(CONSENT_KEY, value);
    setVisible(false);
  }

  if (!visible) return null;

  return (
    <section
      aria-label="Cookie preferences"
      className="scrim fixed bottom-4 left-4 z-50 w-[min(440px,calc(100vw-2rem))] border border-[var(--line)] p-4 shadow-2xl"
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-[var(--ink-strong)]">
            Cookie preferences
          </p>
          <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
            Essential cookies keep sessions and saved analyses working.
            Analytics stay off unless you allow them.
          </p>
        </div>
        <button
          type="button"
          aria-label="Dismiss cookie preferences"
          onClick={() => choose("essential")}
          className="grid size-8 shrink-0 place-items-center text-[var(--muted)] hover:text-white"
        >
          <X size={16} />
        </button>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={() => choose("analytics")}
          className="h-9 bg-[var(--signal)] px-3 text-xs font-bold text-black hover:bg-[var(--signal-strong)]"
        >
          Allow analytics
        </button>
        <button
          type="button"
          onClick={() => choose("essential")}
          className="h-9 border border-[var(--line)] px-3 text-xs font-semibold text-[var(--ink)] hover:bg-[var(--surface-soft)]"
        >
          Essential only
        </button>
      </div>
    </section>
  );
}
