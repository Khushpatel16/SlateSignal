"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CalendarClock,
  CalendarRange,
  CircleAlert,
  Clock3,
  Database,
  GitCommitHorizontal,
  LoaderCircle,
  Search,
  ShieldCheck,
  Activity,
} from "lucide-react";

import { ForecastRange } from "@/components/movies/forecast-range";
import { MoviePoster } from "@/components/movies/movie-poster";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { MovieSummary } from "@/types/domain";

const UPCOMING_QUERY =
  "status=confirmed&status=date_tentative&status=year_only&status=in_theaters&limit=60";

export function RealForecastDesk() {
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [query, setQuery] = useState("");
  const [freshness, setFreshness] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .movies(UPCOMING_QUERY)
      .then((response) => {
        if (!active) return;
        setMovies(response.items);
        setFreshness(response.data_freshness);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const featured =
    movies.find((movie) => movie.slug === "dune-part-three-2026") ??
    movies.find((movie) => movie.backdrop_url) ??
    movies[0];
  const filtered = useMemo(() => {
    const needle = query.trim().toLocaleLowerCase();
    if (!needle) return movies;
    return movies.filter((movie) =>
      [movie.title, movie.director, movie.studio, ...movie.genres]
        .filter(Boolean)
        .some((value) => value?.toLocaleLowerCase().includes(needle)),
    );
  }, [movies, query]);
  const collisionCount = movies.filter(
    (movie) => movie.release_date === "2026-12-18",
  ).length;

  if (!featured && !failed) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <LoaderCircle size={18} className="animate-spin" />
          Loading the forecast ledger
        </div>
      </div>
    );
  }

  if (failed || !featured) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-24">
        <CircleAlert size={28} className="text-[var(--warning)]" />
        <h1 className="mt-5 text-2xl font-extrabold text-white">
          Forecast service unavailable
        </h1>
        <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
          The interface will not substitute fictional films or fabricated
          forecasts. Start the API and refresh this desk.
        </p>
      </div>
    );
  }

  const forecast = featured.forecast;
  return (
    <div>
      <section className="relative min-h-[430px] overflow-hidden border-b border-[var(--line)]">
        {featured.backdrop_url ? (
          <Image
            src={featured.backdrop_url}
            alt={`${featured.title} official promotional artwork`}
            fill
            priority
            sizes="(min-width: 1024px) calc(100vw - 248px), 100vw"
            className="object-cover object-center"
          />
        ) : (
          <div className="surface-grid absolute inset-0 bg-[#151517]" />
        )}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(7,7,8,0.96)_0%,rgba(7,7,8,0.78)_46%,rgba(7,7,8,0.2)_100%)]" />
        <div className="absolute inset-x-0 bottom-0 h-32 bg-[linear-gradient(0deg,#0c0c0d,transparent)]" />

        <div className="relative mx-auto flex min-h-[430px] max-w-[1500px] items-end px-5 py-8 sm:px-8 lg:px-10">
          <div className="max-w-3xl">
            <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase">
              <span className="bg-[var(--signal)] px-2 py-1 text-black">
                Locked real-film forecast
              </span>
              <span className="border border-white/25 px-2 py-1 text-white/75">
                {forecast.model_version ?? "Awaiting model"}
              </span>
              <span className="flex items-center gap-1.5 text-white/65">
                <CalendarClock size={13} />
                {featured.release_date
                  ? formatDate(featured.release_date)
                  : featured.release_year}
              </span>
            </div>
            <h1 className="font-editorial mt-5 text-5xl leading-[0.92] font-medium text-white sm:text-7xl">
              {featured.title}
            </h1>
            <p className="mt-4 line-clamp-2 max-w-2xl text-sm leading-6 text-white/70">
              {featured.synopsis ?? "Official synopsis has not been published."}
            </p>

            <div className="mt-7 grid max-w-2xl gap-6 sm:grid-cols-[270px_1fr] sm:items-end">
              <div>
                <p className="text-[10px] font-bold text-white/55 uppercase">
                  Worldwide final gross
                </p>
                {forecast.p50 !== null ? (
                  <p className="tabular mt-1 text-4xl font-extrabold text-white">
                    {formatMoney(forecast.p50, 0)}
                  </p>
                ) : (
                  <p className="mt-2 text-lg font-bold text-[var(--muted)]">
                    Not enough evidence
                  </p>
                )}
              </div>
              {forecast.p10 !== null &&
                forecast.p50 !== null &&
                forecast.p90 !== null && (
                  <ForecastRange
                    p10={forecast.p10}
                    p50={forecast.p50}
                    p90={forecast.p90}
                  />
                )}
            </div>

            <Link
              href={`/movies/${featured.slug}`}
              className="mt-7 inline-flex h-11 items-center gap-2 bg-[var(--signal)] px-4 text-sm font-extrabold text-black hover:bg-[var(--signal-strong)]"
            >
              Open evidence report
              <ArrowRight size={17} />
            </Link>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10">
        <section className="grid border-y border-[var(--line)] sm:grid-cols-4">
          <DeskMetric
            icon={<Database size={15} />}
            label="Research corpus"
            value="6,437"
            detail="1970-2025 real films"
          />
          <DeskMetric
            icon={<GitCommitHorizontal size={15} />}
            label="Ledger locks"
            value={String(
              movies.filter((movie) => movie.forecast.ledger_hash).length,
            )}
            detail="immutable launch forecasts"
          />
          <DeskMetric
            icon={<CalendarRange size={15} />}
            label="Dec 18 collision"
            value={String(collisionCount)}
            detail="confirmed same-day releases"
          />
          <DeskMetric
            icon={<ShieldCheck size={15} />}
            label="Fairness posture"
            value="Bias-aware"
            detail="protected inputs excluded"
          />
        </section>

        <section className="mt-10">
          <div className="flex flex-col gap-4 border-b border-[var(--line)] pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
                US theatrical calendar
              </p>
              <h2 className="mt-1 text-2xl font-extrabold text-white">
                Upcoming forecast slate
              </h2>
            </div>
            <label className="flex h-10 w-full items-center border border-[var(--line)] bg-[var(--surface)] sm:w-80">
              <Search size={16} className="ml-3 text-[var(--muted)]" />
              <span className="sr-only">Search upcoming films</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Title, director, studio, genre"
                className="h-full min-w-0 flex-1 bg-transparent px-3 text-xs text-white placeholder:text-[#77756f] focus:outline-none"
              />
            </label>
          </div>

          <div className="grid border-t border-l border-[var(--line)] sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((movie, index) => (
              <MovieSignal key={movie.id} movie={movie} priority={index < 2} />
            ))}
          </div>
          {filtered.length === 0 && (
            <p className="border-x border-b border-[var(--line)] px-5 py-14 text-center text-sm text-[var(--muted)]">
              No source-backed titles match that search.
            </p>
          )}
        </section>

        <footer className="mt-6 flex flex-col gap-2 text-[10px] leading-4 text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between">
          <p>
            This product uses the TMDB API but is not endorsed or certified by
            TMDB.
          </p>
          <p className="flex items-center gap-1.5">
            <Clock3 size={12} />
            Data observed{" "}
            {freshness
              ? new Intl.DateTimeFormat("en-US", {
                  dateStyle: "medium",
                  timeStyle: "short",
                }).format(new Date(freshness))
              : "at source sync"}
          </p>
        </footer>
      </div>
    </div>
  );
}

function MovieSignal({
  movie,
  priority,
}: {
  movie: MovieSummary;
  priority: boolean;
}) {
  const forecast = movie.forecast;
  return (
    <Link
      href={`/movies/${movie.slug}`}
      className="group grid min-h-52 grid-cols-[112px_1fr] gap-4 border-r border-b border-[var(--line)] bg-[var(--canvas)] p-4 hover:bg-[var(--canvas-raised)]"
    >
      <MoviePoster
        title={movie.title}
        src={movie.poster_url}
        priority={priority}
        className="border border-[var(--line-soft)]"
      />
      <div className="flex min-w-0 flex-col">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[9px] font-bold text-[var(--signal)] uppercase">
            {movie.release_status.replaceAll("_", " ")}
          </span>
          <span className="tabular text-[9px] text-[var(--muted)]">
            {movie.countdown_days !== null
              ? movie.countdown_days >= 0
                ? `T-${movie.countdown_days}`
                : `T+${Math.abs(movie.countdown_days)}`
              : movie.release_year}
          </span>
        </div>
        <h3 className="mt-2 line-clamp-2 text-base leading-5 font-extrabold text-white">
          {movie.title}
        </h3>
        <p className="mt-1 text-[10px] leading-4 text-[var(--muted)]">
          {movie.director ?? "Director not announced"} ·{" "}
          {movie.release_date
            ? formatDate(movie.release_date)
            : movie.release_year}
        </p>
        <div className="mt-auto pt-4">
          {forecast.p50 !== null &&
          forecast.p10 !== null &&
          forecast.p90 !== null ? (
            <>
              <div className="flex items-end justify-between">
                <span className="text-[9px] font-bold text-[var(--muted)] uppercase">
                  P50 worldwide
                </span>
                <span className="tabular text-lg font-extrabold text-white">
                  {formatMoney(forecast.p50, 0)}
                </span>
              </div>
              <ForecastRange
                p10={forecast.p10}
                p50={forecast.p50}
                p90={forecast.p90}
                compact
              />
            </>
          ) : (
            <div className="flex items-center gap-2 text-[10px] text-[var(--muted)]">
              <Activity size={14} />
              Forecast awaits source-complete inputs
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}

function DeskMetric({
  icon,
  label,
  value,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="border-b border-[var(--line)] py-4 last:border-b-0 sm:border-r sm:border-b-0 sm:px-5 sm:first:pl-0 sm:last:border-r-0">
      <div className="flex items-center gap-2 text-[var(--muted)]">
        {icon}
        <span className="text-[9px] font-bold uppercase">{label}</span>
      </div>
      <p className="tabular mt-2 text-2xl font-extrabold text-white">{value}</p>
      <p className="mt-1 text-[10px] text-[var(--muted)]">{detail}</p>
    </div>
  );
}
