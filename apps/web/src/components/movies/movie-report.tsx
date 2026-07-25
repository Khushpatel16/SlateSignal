"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowLeft,
  CalendarDays,
  Check,
  CircleAlert,
  Clock3,
  Copy,
  Download,
  ExternalLink,
  Fingerprint,
  Gauge,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

import { ForecastRange } from "@/components/movies/forecast-range";
import { MoviePoster } from "@/components/movies/movie-poster";
import { api } from "@/lib/api";
import { formatDate, formatMoney, formatPercent } from "@/lib/format";
import type {
  BuzzPoint,
  ForecastHistoryPoint,
  MovieDetail,
  MovieForecast,
} from "@/types/domain";

export function MovieReport({ slug }: { slug: string }) {
  const [movie, setMovie] = useState<MovieDetail | null>(null);
  const [forecast, setForecast] = useState<MovieForecast | null>(null);
  const [history, setHistory] = useState<ForecastHistoryPoint[]>([]);
  const [buzz, setBuzz] = useState<BuzzPoint[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([
      api.movie(slug),
      api.movieForecast(slug).catch(() => null),
      api.forecastHistory(slug),
      api.buzz(slug),
    ])
      .then(([detail, current, timeline, demand]) => {
        if (!active) return;
        setMovie(detail);
        setForecast(current);
        setHistory(timeline);
        setBuzz(demand);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, [slug]);

  const factorData = useMemo(
    () =>
      (forecast?.grouped_factors ?? [])
        .filter((factor) => factor.impact !== null)
        .sort(
          (left, right) =>
            Math.abs(right.impact ?? 0) - Math.abs(left.impact ?? 0),
        )
        .slice(0, 10)
        .map((factor) => ({
          name: factor.label,
          impact: factor.impact,
          direction: factor.direction,
        })),
    [forecast],
  );
  const timelineData = history.map((item) => ({
    cutoff: new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
    }).format(new Date(item.data_cutoff)),
    p10: item.worldwide?.p10 ?? null,
    p50: item.worldwide?.p50 ?? null,
    p90: item.worldwide?.p90 ?? null,
    actual: item.actual_worldwide,
  }));

  if (!movie && !failed) {
    return (
      <div className="grid min-h-[70vh] place-items-center">
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <LoaderCircle size={18} className="animate-spin" />
          Assembling source evidence
        </div>
      </div>
    );
  }
  if (failed || !movie) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-24">
        <CircleAlert size={28} className="text-[var(--warning)]" />
        <h1 className="mt-4 text-2xl font-extrabold text-white">
          Film report unavailable
        </h1>
        <Link
          href="/"
          className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-[var(--signal)]"
        >
          <ArrowLeft size={16} />
          Return to forecast desk
        </Link>
      </div>
    );
  }

  const worldwide = forecast?.targets.worldwide_total ?? null;
  const actualWorldwide = forecast?.actuals.worldwide_total ?? null;
  const worldwideError = forecast?.errors.worldwide_total ?? null;
  const percentageError =
    actualWorldwide && worldwideError !== null && actualWorldwide.amount > 0
      ? worldwideError / actualWorldwide.amount
      : null;
  return (
    <article className="print-report">
      <header className="relative min-h-[420px] overflow-hidden border-b border-[var(--line)]">
        {movie.backdrop_url && (
          <Image
            src={movie.backdrop_url}
            alt={`${movie.title} official promotional artwork`}
            fill
            priority
            sizes="(min-width: 1024px) calc(100vw - 248px), 100vw"
            className="object-cover"
          />
        )}
        {!movie.backdrop_url && (
          <div className="surface-grid absolute inset-0 bg-[#111113]" />
        )}
        {movie.backdrop_url && (
          <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(7,7,8,0.98)_0%,rgba(7,7,8,0.79)_52%,rgba(7,7,8,0.28)_100%)]" />
        )}
        <div className="relative mx-auto grid min-h-[420px] max-w-[1500px] grid-cols-[112px_1fr] items-end gap-5 px-5 py-8 sm:grid-cols-[180px_1fr] sm:px-8 lg:px-10">
          <MoviePoster
            title={movie.title}
            src={movie.poster_url}
            priority
            className="border border-white/15 shadow-2xl"
          />
          <div className="min-w-0 pb-1">
            <Link
              href="/"
              className="mb-6 inline-flex items-center gap-1.5 text-[10px] font-bold text-white/55 uppercase hover:text-white"
            >
              <ArrowLeft size={13} />
              Forecast desk
            </Link>
            <div className="flex flex-wrap items-center gap-2 text-[9px] font-bold uppercase">
              <span className="bg-[var(--signal)] px-2 py-1 text-black">
                {forecast ? "Ledger locked" : "Forecast pending"}
              </span>
              <span className="border border-white/25 px-2 py-1 text-white/70">
                {movie.release_status.replaceAll("_", " ")}
              </span>
              {forecast && (
                <span className="border border-white/25 px-2 py-1 text-white/70">
                  {forecast.forecast_type === "evaluation"
                    ? "Retrospective evaluation"
                    : "Official pre-release forecast"}
                </span>
              )}
            </div>
            <h1 className="font-editorial mt-4 text-4xl leading-[0.95] font-medium text-white sm:text-6xl">
              {movie.title}
            </h1>
            <p className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-white/60 sm:text-xs">
              <span className="flex items-center gap-1.5">
                <CalendarDays size={13} />
                {movie.release_date
                  ? formatDate(movie.release_date)
                  : movie.release_year}
              </span>
              <span>{movie.director ?? "Director not announced"}</span>
              <span>{movie.genres.join(" / ")}</span>
            </p>
            <p className="mt-4 line-clamp-3 max-w-3xl text-xs leading-5 text-white/65 sm:text-sm sm:leading-6">
              {movie.synopsis ?? "Official synopsis has not been published."}
            </p>
          </div>
        </div>
      </header>

      <section className="border-b border-[var(--line)] bg-[var(--canvas-raised)]">
        <div className="mx-auto grid max-w-[1500px] gap-8 px-5 py-7 sm:px-8 lg:grid-cols-[1fr_340px] lg:px-10">
          <div>
            <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
              Predicted worldwide final gross
            </p>
            {worldwide ? (
              <>
                <div className="mt-2 flex flex-wrap items-end gap-x-5 gap-y-2">
                  <p className="tabular text-4xl font-extrabold text-white sm:text-5xl">
                    {formatMoney(worldwide.p50, 0)}
                  </p>
                  <p className="pb-1 text-xs text-[var(--muted)]">
                    80% split-conformal interval
                  </p>
                  {actualWorldwide && (
                    <div className="border-l border-[var(--line)] pl-5">
                      <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
                        Final reported actual
                      </p>
                      <p className="tabular mt-1 text-2xl font-extrabold text-white">
                        {formatMoney(actualWorldwide.amount, 0)}
                      </p>
                      {worldwideError !== null && (
                        <p className="mt-1 text-[10px] text-[var(--muted)]">
                          Error {formatMoney(worldwideError, 0)}
                          {percentageError !== null
                            ? ` · ${formatPercent(percentageError)}`
                            : ""}
                        </p>
                      )}
                    </div>
                  )}
                </div>
                <div className="mt-5 max-w-3xl">
                  <ForecastRange
                    p10={worldwide.p10}
                    p50={worldwide.p50}
                    p90={worldwide.p90}
                    compact
                  />
                </div>
              </>
            ) : (
              <p className="mt-3 text-xl font-bold text-[var(--muted)]">
                Insufficient source-complete inputs
              </p>
            )}
          </div>
          <div className="grid grid-cols-2 border border-[var(--line)]">
            <ReportMetric
              label="Confidence"
              value={
                forecast ? formatPercent(forecast.confidence_score) : "Pending"
              }
              icon={<Gauge size={14} />}
            />
            <ReportMetric
              label="Horizon"
              value={
                forecast?.horizon_days !== null &&
                forecast?.horizon_days !== undefined
                  ? `T-${forecast.horizon_days}`
                  : "N/A"
              }
              icon={<Clock3 size={14} />}
            />
            <ReportMetric
              label="Model"
              value={forecast?.model_version ?? "N/A"}
              icon={<Check size={14} />}
            />
            <ReportMetric
              label="Fairness"
              value={
                forecast?.fairness.audit_status.replaceAll("_", " ") ??
                "Pending"
              }
              icon={<ShieldCheck size={14} />}
            />
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1500px] px-5 py-9 sm:px-8 lg:px-10">
        <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_360px]">
          <div className="min-w-0 space-y-12">
            <ReportSection
              eyebrow="Forecast time machine"
              title="Prediction evolution"
              detail="Each point is an immutable forecast with its own cutoff and ledger hash."
            >
              <div className="h-72 border-y border-[var(--line)] py-4">
                {timelineData.length ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={timelineData}>
                      <CartesianGrid
                        stroke="#29292d"
                        vertical={false}
                        strokeDasharray="3 3"
                      />
                      <XAxis
                        dataKey="cutoff"
                        tick={{ fill: "#8f8d87", fontSize: 10 }}
                        axisLine={{ stroke: "#39393d" }}
                        tickLine={false}
                      />
                      <YAxis
                        tickFormatter={(value) => formatMoney(Number(value), 0)}
                        tick={{ fill: "#8f8d87", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        width={58}
                      />
                      <ChartTooltip
                        contentStyle={{
                          background: "#171719",
                          border: "1px solid #303034",
                          borderRadius: 0,
                          fontSize: 11,
                        }}
                        formatter={(value) =>
                          typeof value === "number"
                            ? formatMoney(value, 0)
                            : "Unavailable"
                        }
                      />
                      <Area
                        type="monotone"
                        dataKey="p90"
                        stroke="#78aee8"
                        fill="#78aee8"
                        fillOpacity={0.08}
                        strokeOpacity={0.35}
                      />
                      <Area
                        type="monotone"
                        dataKey="p10"
                        stroke="#78aee8"
                        fill="#0c0c0d"
                        fillOpacity={1}
                        strokeOpacity={0.35}
                      />
                      <Area
                        type="monotone"
                        dataKey="p50"
                        stroke="#f0c94c"
                        fill="transparent"
                        strokeWidth={2}
                      />
                      <ReferenceLine
                        y={movie.worldwide_actual?.amount}
                        stroke="#68c6a3"
                        strokeDasharray="5 4"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="grid h-full place-items-center text-xs text-[var(--muted)]">
                    The first milestone forecast has not been sealed.
                  </div>
                )}
              </div>
            </ReportSection>

            <ReportSection
              eyebrow="Attribution"
              title="Factor evidence"
              detail="Only modeled factors receive dollar attribution. Unavailable factors remain visible below."
            >
              {factorData.length ? (
                <div className="h-80 border-y border-[var(--line)] py-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={factorData}
                      layout="vertical"
                      margin={{ left: 12, right: 28 }}
                    >
                      <CartesianGrid
                        stroke="#29292d"
                        horizontal={false}
                        strokeDasharray="3 3"
                      />
                      <XAxis
                        type="number"
                        tickFormatter={(value) => formatMoney(Number(value), 0)}
                        tick={{ fill: "#8f8d87", fontSize: 9 }}
                        axisLine={{ stroke: "#39393d" }}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={120}
                        tick={{ fill: "#c9c6bd", fontSize: 9 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <ChartTooltip
                        cursor={{ fill: "rgba(255,255,255,0.03)" }}
                        contentStyle={{
                          background: "#171719",
                          border: "1px solid #303034",
                          borderRadius: 0,
                          fontSize: 11,
                        }}
                        formatter={(value) =>
                          typeof value === "number"
                            ? formatMoney(value, 0)
                            : "Unavailable"
                        }
                      />
                      <ReferenceLine x={0} stroke="#77756f" />
                      <Bar dataKey="impact">
                        {factorData.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={
                              entry.direction === "positive"
                                ? "#68c6a3"
                                : entry.direction === "negative"
                                  ? "#ef746b"
                                  : "#8f8d87"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="border-y border-[var(--line)] py-10 text-sm text-[var(--muted)]">
                  Model attribution is unavailable for this forecast artifact.
                </p>
              )}
              <div className="mt-4 grid border-t border-[var(--line)] sm:grid-cols-2">
                {(forecast?.grouped_factors ?? []).map((factor) => (
                  <div
                    key={factor.key}
                    className="border-b border-[var(--line)] py-3 sm:odd:pr-5 sm:even:border-l sm:even:pl-5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-xs font-bold text-white">
                        {factor.label}
                      </p>
                      <span
                        className={`text-[9px] font-bold uppercase ${
                          factor.direction === "unknown"
                            ? "text-[var(--muted)]"
                            : factor.direction === "positive"
                              ? "text-[var(--positive)]"
                              : factor.direction === "negative"
                                ? "text-[var(--negative)]"
                                : "text-[var(--info)]"
                        }`}
                      >
                        {factor.direction}
                      </span>
                    </div>
                    <p className="mt-1 text-[10px] text-[var(--muted-strong)]">
                      {factor.value}
                    </p>
                    <p className="mt-1.5 text-[10px] leading-4 text-[var(--muted)]">
                      {factor.evidence}
                    </p>
                  </div>
                ))}
              </div>
            </ReportSection>

            <ReportSection
              eyebrow="Demand signals"
              title="Pre-release buzz"
              detail="Timestamped aggregates are shown without post-release leakage or hand-authored revenue multipliers."
            >
              {buzz.length ? (
                <div className="divide-y divide-[var(--line)] border-y border-[var(--line)]">
                  {buzz.map((point) => (
                    <a
                      key={`${point.source}-${point.metric}-${point.observed_at}`}
                      href={point.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="grid grid-cols-[1fr_auto] gap-4 py-3 hover:bg-[var(--surface)]"
                    >
                      <div>
                        <p className="text-xs font-bold text-white">
                          {point.source} · {point.metric}
                        </p>
                        <p className="mt-1 text-[10px] text-[var(--muted)]">
                          Observed{" "}
                          {new Date(point.observed_at).toLocaleString()}
                        </p>
                      </div>
                      <p className="tabular text-sm font-extrabold text-white">
                        {point.value.toLocaleString()}
                      </p>
                    </a>
                  ))}
                </div>
              ) : (
                <p className="border-y border-[var(--line)] py-8 text-xs leading-5 text-[var(--muted)]">
                  No approved pre-cutoff buzz observations are available. The
                  interval remains wide; the system does not invent attention
                  scores.
                </p>
              )}
            </ReportSection>
          </div>

          <aside className="space-y-8">
            <section className="border border-[var(--line)] bg-[var(--surface)] p-4">
              <div className="flex items-center gap-2 text-xs font-extrabold text-white">
                <Fingerprint size={16} className="text-[var(--signal)]" />
                Forecast ledger
              </div>
              {forecast ? (
                <>
                  <p className="mt-3 font-mono text-[9px] leading-4 break-all text-[var(--muted)]">
                    {forecast.ledger_hash}
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      aria-label="Copy ledger hash"
                      onClick={() => {
                        void navigator.clipboard.writeText(
                          forecast.ledger_hash,
                        );
                        toast.success("Ledger hash copied");
                      }}
                      className="grid size-9 place-items-center border border-[var(--line)] text-[var(--muted)] hover:text-white"
                    >
                      <Copy size={15} />
                    </button>
                    <button
                      type="button"
                      aria-label="Download report"
                      onClick={() => window.print()}
                      className="flex h-9 items-center gap-2 border border-[var(--line)] px-3 text-[10px] font-bold text-[var(--muted-strong)] hover:bg-[var(--surface-soft)] hover:text-white"
                    >
                      <Download size={14} />
                      Download report
                    </button>
                  </div>
                </>
              ) : (
                <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
                  A hash is created only after a forecast is sealed.
                </p>
              )}
            </section>

            <section>
              <h2 className="text-sm font-extrabold text-white">Comparables</h2>
              <div className="mt-3 border-t border-[var(--line)]">
                {(forecast?.comparables ?? []).map((item) => (
                  <Link
                    key={item.movie_id}
                    href={`/movies/${item.slug}`}
                    className="flex items-center justify-between gap-4 border-b border-[var(--line)] py-3"
                  >
                    <span className="min-w-0">
                      <span className="block truncate text-xs font-bold text-white">
                        {item.title}
                      </span>
                      <span className="mt-0.5 block text-[9px] text-[var(--muted)]">
                        {item.release_year} · {formatPercent(item.similarity)}
                      </span>
                    </span>
                    <span className="tabular text-[10px] font-bold text-[var(--muted-strong)]">
                      {item.actual_worldwide
                        ? formatMoney(item.actual_worldwide, 0)
                        : "N/A"}
                    </span>
                  </Link>
                ))}
                {!forecast?.comparables.length && (
                  <p className="border-b border-[var(--line)] py-5 text-[10px] text-[var(--muted)]">
                    No source-complete comparables available.
                  </p>
                )}
              </div>
            </section>

            <section>
              <div className="flex items-center gap-2">
                <ShieldCheck size={15} className="text-[var(--signal)]" />
                <h2 className="text-sm font-extrabold text-white">
                  Fairness status
                </h2>
              </div>
              <p className="mt-3 text-xs leading-5 text-[var(--muted)]">
                {forecast?.fairness.cohort_definition ??
                  "Fairness evaluation is pending."}
              </p>
              <ul className="mt-3 space-y-2">
                {(forecast?.fairness.notes ?? []).map((note) => (
                  <li
                    key={note}
                    className="border-l-2 border-[var(--line)] pl-3 text-[10px] leading-4 text-[var(--muted)]"
                  >
                    {note}
                  </li>
                ))}
              </ul>
            </section>

            <section>
              <h2 className="text-sm font-extrabold text-white">Sources</h2>
              <div className="mt-3 border-t border-[var(--line)]">
                {movie.evidence.slice(0, 12).map((item) => (
                  <a
                    key={item.raw_checksum}
                    href={item.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center justify-between gap-3 border-b border-[var(--line)] py-3 text-[10px] text-[var(--muted)] hover:text-white"
                  >
                    <span className="min-w-0">
                      <span className="block font-bold text-[var(--muted-strong)]">
                        {item.source}
                      </span>
                      <span className="block truncate">
                        {item.observation_type} ·{" "}
                        {formatPercent(item.confidence)}
                      </span>
                    </span>
                    <ExternalLink size={13} className="shrink-0" />
                  </a>
                ))}
              </div>
            </section>

            {forecast?.limitations.length ? (
              <section className="border-t border-[var(--line)] pt-5">
                <h2 className="text-xs font-extrabold text-white">
                  Limitations
                </h2>
                <ul className="mt-3 space-y-2">
                  {forecast.limitations.map((item) => (
                    <li
                      key={item}
                      className="text-[10px] leading-4 text-[var(--muted)]"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            ) : null}
          </aside>
        </div>
      </section>
    </article>
  );
}

function ReportSection({
  eyebrow,
  title,
  detail,
  children,
}: {
  eyebrow: string;
  title: string;
  detail: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <p className="text-[9px] font-bold text-[var(--signal)] uppercase">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-xl font-extrabold text-white">{title}</h2>
      <p className="mt-2 max-w-2xl text-xs leading-5 text-[var(--muted)]">
        {detail}
      </p>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function ReportMetric({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="min-w-0 border-r border-b border-[var(--line)] p-3 last:border-b-0 odd:last:border-b-0 even:border-r-0">
      <div className="flex items-center gap-1.5 text-[var(--muted)]">
        {icon}
        <span className="text-[8px] font-bold uppercase">{label}</span>
      </div>
      <p className="mt-1.5 truncate text-xs font-extrabold text-white">
        {value}
      </p>
    </div>
  );
}
