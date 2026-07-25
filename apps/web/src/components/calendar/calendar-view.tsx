"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  CalendarDays,
  ChevronRight,
  CircleAlert,
  Filter,
  LoaderCircle,
} from "lucide-react";

import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { MovieSummary, ReleaseStatus } from "@/types/domain";

const years = [2026, 2027, 2028, 2029, 2030];

export function CalendarView() {
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [year, setYear] = useState(2026);
  const [status, setStatus] = useState<ReleaseStatus | "all">("all");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .movies(
        "status=confirmed&status=date_tentative&status=year_only&status=in_theaters&limit=100",
      )
      .then((response) => {
        if (active) setMovies(response.items);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const visible = useMemo(
    () =>
      movies.filter(
        (movie) =>
          movie.release_year === year &&
          (status === "all" || movie.release_status === status),
      ),
    [movies, status, year],
  );
  const grouped = useMemo(() => {
    const output = new Map<string, MovieSummary[]>();
    for (const movie of visible) {
      const month = movie.release_date
        ? new Intl.DateTimeFormat("en-US", {
            month: "long",
            timeZone: "UTC",
          }).format(new Date(`${movie.release_date}T00:00:00Z`))
        : "Date pending";
      output.set(month, [...(output.get(month) ?? []), movie]);
    }
    return output;
  }, [visible]);

  return (
    <div className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10">
      <header className="border-b border-[var(--line)] pb-6">
        <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
          Confirmed US theatrical releases
        </p>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-white">
              Release calendar
            </h1>
            <p className="mt-2 max-w-2xl text-xs leading-5 text-[var(--muted)]">
              Date confidence is preserved from source records. Year-only and
              tentative films are never assigned an invented day.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div
              className="flex border border-[var(--line)]"
              aria-label="Release year"
            >
              {years.map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setYear(item)}
                  className={`h-9 border-r border-[var(--line)] px-3 text-[10px] font-bold last:border-r-0 ${
                    year === item
                      ? "bg-[var(--signal)] text-black"
                      : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white"
                  }`}
                >
                  {item}
                </button>
              ))}
            </div>
            <label className="flex h-9 items-center border border-[var(--line)] bg-[var(--surface)]">
              <Filter size={13} className="ml-2.5 text-[var(--muted)]" />
              <span className="sr-only">Filter by confirmation status</span>
              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value as ReleaseStatus | "all")
                }
                className="h-full bg-transparent px-2.5 text-[10px] font-bold text-[var(--muted-strong)] focus:outline-none"
              >
                <option value="all">All states</option>
                <option value="confirmed">Confirmed</option>
                <option value="date_tentative">Tentative</option>
                <option value="year_only">Year only</option>
                <option value="in_theaters">In theaters</option>
              </select>
            </label>
          </div>
        </div>
      </header>

      {!movies.length && !failed ? (
        <div className="grid h-80 place-items-center">
          <div className="flex items-center gap-2 text-xs text-[var(--muted)]">
            <LoaderCircle size={17} className="animate-spin" />
            Loading release records
          </div>
        </div>
      ) : failed ? (
        <div className="flex items-center gap-3 border-b border-[var(--line)] py-10 text-sm text-[var(--warning)]">
          <CircleAlert size={18} />
          Release data is unavailable.
        </div>
      ) : (
        <div>
          {[...grouped.entries()].map(([month, titles]) => (
            <section
              key={month}
              className="grid border-b border-[var(--line)] lg:grid-cols-[170px_1fr]"
            >
              <div className="py-5 lg:border-r lg:border-[var(--line)] lg:pr-5">
                <p className="font-editorial text-2xl text-white">{month}</p>
                <p className="mt-1 text-[9px] font-bold text-[var(--muted)] uppercase">
                  {titles.length} {titles.length === 1 ? "release" : "releases"}
                </p>
              </div>
              <div className="lg:pl-6">
                {titles.map((movie) => {
                  const sameDay = movie.release_date
                    ? visible.filter(
                        (candidate) =>
                          candidate.release_date === movie.release_date,
                      ).length
                    : 0;
                  return (
                    <Link
                      key={movie.id}
                      href={`/movies/${movie.slug}`}
                      className="group grid gap-3 border-t border-[var(--line)] py-4 first:border-t-0 sm:grid-cols-[105px_minmax(0,1fr)_150px_24px] sm:items-center"
                    >
                      <div>
                        <p className="tabular text-xs font-extrabold text-white">
                          {movie.release_date
                            ? formatDate(movie.release_date)
                            : `${movie.release_year} · TBD`}
                        </p>
                        <p className="mt-1 text-[9px] font-bold text-[var(--muted)] uppercase">
                          {movie.release_status.replaceAll("_", " ")}
                        </p>
                      </div>
                      <div className="min-w-0">
                        <h2 className="truncate text-sm font-extrabold text-white group-hover:text-[var(--signal)]">
                          {movie.title}
                        </h2>
                        <p className="mt-1 truncate text-[10px] text-[var(--muted)]">
                          {movie.director ?? "Director not announced"} ·{" "}
                          {movie.genres.join(" / ")}
                        </p>
                        {sameDay > 1 && (
                          <p className="mt-1 flex items-center gap-1 text-[9px] font-bold text-[var(--warning)] uppercase">
                            <CalendarDays size={11} />
                            {sameDay}-film date collision
                          </p>
                        )}
                      </div>
                      <div className="sm:text-right">
                        <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
                          P50 worldwide
                        </p>
                        <p className="tabular mt-1 text-sm font-extrabold text-white">
                          {movie.forecast.p50 !== null
                            ? formatMoney(movie.forecast.p50, 0)
                            : "Pending"}
                        </p>
                      </div>
                      <ChevronRight
                        size={16}
                        className="hidden text-[var(--muted)] sm:block"
                      />
                    </Link>
                  );
                })}
              </div>
            </section>
          ))}
          {!visible.length && (
            <p className="py-16 text-center text-sm text-[var(--muted)]">
              No confirmed source records in this slice yet.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
