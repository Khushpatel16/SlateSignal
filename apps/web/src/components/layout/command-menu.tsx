"use client";

import * as Dialog from "@radix-ui/react-dialog";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Bookmark,
  CalendarDays,
  FlaskConical,
  GitCompareArrows,
  LayoutDashboard,
  LineChart,
  LoaderCircle,
  Microscope,
  Search,
  ShieldCheck,
  X,
} from "lucide-react";

import { api } from "@/lib/api";
import { formatMoney } from "@/lib/format";
import type { MovieSummary } from "@/types/domain";

const destinations = [
  {
    href: "/",
    label: "Forecast desk",
    detail: "Real upcoming films and locked forecasts",
    icon: LayoutDashboard,
  },
  {
    href: "/calendar",
    label: "Release calendar",
    detail: "Confirmed US theatrical dates through 2030",
    icon: CalendarDays,
  },
  {
    href: "/compare",
    label: "Collision compare",
    detail: "Compare forecasts and release-window pressure",
    icon: GitCompareArrows,
  },
  {
    href: "/backtests",
    label: "Locked backtests",
    detail: "Historical forecasts against final actuals",
    icon: LineChart,
  },
  {
    href: "/research",
    label: "Research",
    detail: "Model tournament, calibration, and fairness evidence",
    icon: Microscope,
  },
  {
    href: "/lab",
    label: "Scenario lab",
    detail: "Explore an original film package",
    icon: FlaskConical,
  },
  {
    href: "/saved",
    label: "Saved work",
    detail: "Return to stored scenarios",
    icon: Bookmark,
  },
  {
    href: "/model-card",
    label: "Model evidence",
    detail: "Architecture, validation, and limitations",
    icon: ShieldCheck,
  },
];

export function CommandMenu({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [query, setQuery] = useState("");
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [movieSearchPending, setMovieSearchPending] = useState(false);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        onOpenChange(!open);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onOpenChange, open]);

  useEffect(() => {
    const normalized = query.trim();
    if (!open || normalized.length < 2) {
      queueMicrotask(() => {
        setMovies([]);
        setMovieSearchPending(false);
      });
      return;
    }

    let active = true;
    const timer = window.setTimeout(() => {
      api
        .movies(`q=${encodeURIComponent(normalized)}&limit=8`)
        .then((response) => {
          if (active) setMovies(response.items);
        })
        .catch(() => {
          if (active) setMovies([]);
        })
        .finally(() => {
          if (active) setMovieSearchPending(false);
        });
    }, 180);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [open, query]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return destinations;
    return destinations.filter(
      (item) =>
        item.label.toLocaleLowerCase().includes(needle) ||
        item.detail.toLocaleLowerCase().includes(needle),
    );
  }, [query]);

  return (
    <Dialog.Root
      open={open}
      onOpenChange={(next) => {
        onOpenChange(next);
        if (!next) {
          setQuery("");
          setMovies([]);
        }
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content className="fixed top-[14vh] left-1/2 z-50 w-[calc(100%-32px)] max-w-xl -translate-x-1/2 border border-[var(--line)] bg-[var(--canvas-raised)] shadow-2xl">
          <Dialog.Title className="sr-only">Search SlateSignal</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search real films or navigate to a SlateSignal workspace.
          </Dialog.Description>
          <div className="flex items-center border-b border-[var(--line)]">
            <Search size={17} className="ml-4 shrink-0 text-[var(--muted)]" />
            <input
              autoFocus
              value={query}
              onChange={(event) => {
                setQuery(event.target.value);
                setMovieSearchPending(event.target.value.trim().length >= 2);
              }}
              placeholder="Search films and workspaces"
              className="h-14 min-w-0 flex-1 bg-transparent px-3 text-sm text-white placeholder:text-[#6f6d67] focus:outline-none"
            />
            <Dialog.Close
              aria-label="Close search"
              className="mr-3 grid size-8 place-items-center text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white"
            >
              <X size={16} />
            </Dialog.Close>
          </div>

          <div className="max-h-[55vh] overflow-y-auto p-2">
            {query.trim().length >= 2 && (
              <div className="mb-2 border-b border-[var(--line)] pb-2">
                <div className="flex h-8 items-center justify-between px-3">
                  <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
                    Real-film catalog
                  </p>
                  {movieSearchPending && (
                    <LoaderCircle
                      size={13}
                      className="animate-spin text-[var(--muted)]"
                    />
                  )}
                </div>
                {movies.map((movie) => (
                  <Link
                    key={movie.id}
                    href={`/movies/${movie.slug}`}
                    onClick={() => onOpenChange(false)}
                    className="grid grid-cols-[1fr_auto] items-center gap-4 border-l-2 border-transparent px-3 py-3 hover:border-[var(--signal)] hover:bg-[var(--surface)]"
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-bold text-white">
                        {movie.title}
                      </span>
                      <span className="mt-1 block text-[10px] text-[var(--muted)]">
                        {movie.release_year} ·{" "}
                        {movie.release_status.replaceAll("_", " ")} ·{" "}
                        {movie.director ?? "Director unavailable"}
                      </span>
                    </span>
                    <span className="text-right">
                      <span className="block text-[9px] font-bold text-[var(--muted)] uppercase">
                        {movie.worldwide_actual
                          ? "Actual worldwide"
                          : "P50 worldwide"}
                      </span>
                      <span className="tabular mt-1 block text-sm font-extrabold text-white">
                        {movie.worldwide_actual
                          ? formatMoney(movie.worldwide_actual.amount, 0)
                          : movie.forecast.p50 !== null
                            ? formatMoney(movie.forecast.p50, 0)
                            : "Unavailable"}
                      </span>
                    </span>
                  </Link>
                ))}
                {!movieSearchPending && movies.length === 0 && (
                  <p className="px-3 py-4 text-xs text-[var(--muted)]">
                    No source-backed film matches this query.
                  </p>
                )}
              </div>
            )}
            {(filtered.length > 0 || query.trim().length < 2) && (
              <p className="flex h-8 items-center px-3 text-[9px] font-bold text-[var(--muted)] uppercase">
                Workspaces
              </p>
            )}
            {filtered.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => onOpenChange(false)}
                  className="flex items-center gap-3 border-l-2 border-transparent px-3 py-3 hover:border-[var(--signal)] hover:bg-[var(--surface)]"
                >
                  <span className="grid size-9 shrink-0 place-items-center bg-[var(--surface)] text-[var(--signal)]">
                    <Icon size={17} />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-bold text-white">
                      {item.label}
                    </span>
                    <span className="mt-0.5 block truncate text-[11px] text-[var(--muted)]">
                      {item.detail}
                    </span>
                  </span>
                </Link>
              );
            })}
            {filtered.length === 0 && query.trim().length < 2 && (
              <p className="px-4 py-10 text-center text-xs text-[var(--muted)]">
                No matching workspace
              </p>
            )}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
