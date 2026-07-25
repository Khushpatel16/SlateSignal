"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowUpRight,
  CalendarRange,
  CircleAlert,
  LoaderCircle,
  Scale,
} from "lucide-react";

import { ForecastRange } from "@/components/movies/forecast-range";
import { api } from "@/lib/api";
import { formatDate, formatMoney } from "@/lib/format";
import type { MovieForecast, MovieSummary } from "@/types/domain";

export function CompareWorkspace() {
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [leftId, setLeftId] = useState("");
  const [rightId, setRightId] = useState("");
  const [forecasts, setForecasts] = useState<
    Record<string, MovieForecast | null>
  >({});
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .movies(
        "status=confirmed&status=date_tentative&status=year_only&status=in_theaters&limit=100",
      )
      .then((response) => {
        if (!active) return;
        setMovies(response.items);
        const dune = response.items.find((item) =>
          item.slug.startsWith("dune-part-three"),
        );
        const avengers = response.items.find((item) =>
          item.slug.startsWith("avengers-doomsday"),
        );
        setLeftId(dune?.id ?? response.items[0]?.id ?? "");
        setRightId(avengers?.id ?? response.items[1]?.id ?? "");
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const ids = [leftId, rightId].filter(
      (id) => id && forecasts[id] === undefined,
    );
    if (!ids.length) return;
    let active = true;
    for (const id of ids) {
      api
        .movieForecast(id)
        .then((forecast) => {
          if (active) {
            setForecasts((current) => ({ ...current, [id]: forecast }));
          }
        })
        .catch(() => {
          if (active) {
            setForecasts((current) => ({ ...current, [id]: null }));
          }
        });
    }
    return () => {
      active = false;
    };
  }, [forecasts, leftId, rightId]);

  const left = movies.find((movie) => movie.id === leftId);
  const right = movies.find((movie) => movie.id === rightId);
  const leftForecast = forecasts[leftId];
  const rightForecast = forecasts[rightId];
  const dateGap = useMemo(() => {
    if (!left?.release_date || !right?.release_date) return null;
    return Math.abs(
      Math.round(
        (new Date(`${left.release_date}T00:00:00Z`).getTime() -
          new Date(`${right.release_date}T00:00:00Z`).getTime()) /
          86_400_000,
      ),
    );
  }, [left, right]);

  return (
    <div className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10">
      <header className="border-b border-[var(--line)] pb-6">
        <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
          Release collision analysis
        </p>
        <h1 className="mt-2 text-3xl font-extrabold text-white">
          Compare forecasts
        </h1>
        <p className="mt-2 max-w-2xl text-xs leading-5 text-[var(--muted)]">
          Compare immutable film forecasts and the pressure created when
          theatrical windows overlap.
        </p>
      </header>

      {failed ? (
        <div className="flex items-center gap-3 py-16 text-sm text-[var(--warning)]">
          <CircleAlert size={18} />
          The comparison catalog is unavailable.
        </div>
      ) : !movies.length ? (
        <div className="grid h-72 place-items-center">
          <LoaderCircle
            size={20}
            className="animate-spin text-[var(--muted)]"
          />
        </div>
      ) : (
        <>
          <section className="grid gap-px border-x border-b border-[var(--line)] bg-[var(--line)] lg:grid-cols-2">
            <FilmColumn
              side="Film A"
              movies={movies}
              selected={leftId}
              onSelect={setLeftId}
              movie={left}
              forecast={leftForecast}
            />
            <FilmColumn
              side="Film B"
              movies={movies}
              selected={rightId}
              onSelect={setRightId}
              movie={right}
              forecast={rightForecast}
            />
          </section>

          <section className="grid border-x border-b border-[var(--line)] sm:grid-cols-3">
            <CollisionMetric
              label="Window distance"
              value={dateGap === null ? "Unknown" : `${dateGap} days`}
              detail={
                dateGap === 0
                  ? "Direct same-day collision"
                  : "Calendar separation"
              }
              warning={dateGap === 0}
            />
            <CollisionMetric
              label="P50 spread"
              value={
                leftForecast?.targets.worldwide_total &&
                rightForecast?.targets.worldwide_total
                  ? formatMoney(
                      Math.abs(
                        leftForecast.targets.worldwide_total.p50 -
                          rightForecast.targets.worldwide_total.p50,
                      ),
                      0,
                    )
                  : "Unavailable"
              }
              detail="Difference in worldwide medians"
            />
            <CollisionMetric
              label="Shared premium pressure"
              value={dateGap !== null && dateGap <= 7 ? "High" : "Lower"}
              detail="Screen and attention competition"
              warning={dateGap !== null && dateGap <= 7}
            />
          </section>

          <section className="mt-10">
            <div className="flex items-center gap-2">
              <Scale size={17} className="text-[var(--signal)]" />
              <h2 className="text-xl font-extrabold text-white">
                Evidence matrix
              </h2>
            </div>
            <div className="mt-4 overflow-x-auto border-t border-[var(--line)]">
              <table className="w-full min-w-[720px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[9px] font-bold text-[var(--muted)] uppercase">
                    <th className="py-3 pr-4">Factor</th>
                    <th className="px-4 py-3">{left?.title}</th>
                    <th className="px-4 py-3">{right?.title}</th>
                  </tr>
                </thead>
                <tbody>
                  {factorRows(leftForecast, rightForecast).map((row) => (
                    <tr
                      key={row.label}
                      className="border-b border-[var(--line)] text-xs"
                    >
                      <th className="py-3 pr-4 font-bold text-white">
                        {row.label}
                      </th>
                      <td className="px-4 py-3 text-[var(--muted-strong)]">
                        {row.left}
                      </td>
                      <td className="px-4 py-3 text-[var(--muted-strong)]">
                        {row.right}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function FilmColumn({
  side,
  movies,
  selected,
  onSelect,
  movie,
  forecast,
}: {
  side: string;
  movies: MovieSummary[];
  selected: string;
  onSelect: (id: string) => void;
  movie: MovieSummary | undefined;
  forecast: MovieForecast | null | undefined;
}) {
  const worldwide = forecast?.targets.worldwide_total;
  return (
    <div className="bg-[var(--canvas)] p-5 sm:p-7">
      <label>
        <span className="text-[9px] font-bold text-[var(--muted)] uppercase">
          {side}
        </span>
        <select
          value={selected}
          onChange={(event) => onSelect(event.target.value)}
          className="mt-2 h-11 w-full border border-[var(--line)] bg-[var(--surface)] px-3 text-sm font-bold text-white focus:outline-none"
        >
          {movies.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title} · {item.release_year}
            </option>
          ))}
        </select>
      </label>
      {movie && (
        <div className="mt-6">
          <p className="flex items-center gap-1.5 text-[10px] text-[var(--muted)]">
            <CalendarRange size={13} />
            {movie.release_date
              ? formatDate(movie.release_date)
              : movie.release_year}
          </p>
          <h2 className="font-editorial mt-2 text-3xl leading-8 text-white">
            {movie.title}
          </h2>
          <p className="mt-2 text-[10px] text-[var(--muted)]">
            {movie.director ?? "Director not announced"} ·{" "}
            {movie.genres.join(" / ")}
          </p>
          <div className="mt-7">
            <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
              Worldwide final gross
            </p>
            {worldwide ? (
              <>
                <p className="tabular mt-1 text-4xl font-extrabold text-white">
                  {formatMoney(worldwide.p50, 0)}
                </p>
                <div className="mt-5">
                  <ForecastRange
                    p10={worldwide.p10}
                    p50={worldwide.p50}
                    p90={worldwide.p90}
                    compact
                  />
                </div>
              </>
            ) : forecast === undefined ? (
              <LoaderCircle
                size={17}
                className="mt-4 animate-spin text-[var(--muted)]"
              />
            ) : (
              <p className="mt-2 text-sm text-[var(--muted)]">
                Forecast unavailable
              </p>
            )}
          </div>
          <Link
            href={`/movies/${movie.slug}`}
            className="mt-6 inline-flex items-center gap-1.5 text-[10px] font-bold text-[var(--signal)] uppercase"
          >
            Full report
            <ArrowUpRight size={13} />
          </Link>
        </div>
      )}
    </div>
  );
}

function CollisionMetric({
  label,
  value,
  detail,
  warning = false,
}: {
  label: string;
  value: string;
  detail: string;
  warning?: boolean;
}) {
  return (
    <div className="border-b border-[var(--line)] p-4 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0">
      <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
        {label}
      </p>
      <p
        className={`mt-1 text-xl font-extrabold ${
          warning ? "text-[var(--warning)]" : "text-white"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-[10px] text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function factorRows(
  left: MovieForecast | null | undefined,
  right: MovieForecast | null | undefined,
) {
  const labels = [
    "Synopsis embedding",
    "Production budget",
    "Genre-market history",
    "Director history",
    "Nearby competition",
    "Premium formats",
    "Wikipedia attention",
    "Trailer momentum",
  ];
  return labels.map((label) => {
    const leftFactor = left?.grouped_factors.find(
      (item) => item.label === label,
    );
    const rightFactor = right?.grouped_factors.find(
      (item) => item.label === label,
    );
    return {
      label,
      left: factorValue(leftFactor),
      right: factorValue(rightFactor),
    };
  });
}

function factorValue(
  factor: MovieForecast["grouped_factors"][number] | undefined,
) {
  if (!factor) return "Unavailable";
  if (factor.impact === null) return factor.value;
  return `${factor.value} · ${
    factor.impact >= 0 ? "+" : ""
  }${formatMoney(factor.impact, 0)}`;
}
