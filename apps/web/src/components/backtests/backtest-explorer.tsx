"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  BarChart3,
  CircleAlert,
  Gauge,
  LoaderCircle,
  Target,
} from "lucide-react";

import { api } from "@/lib/api";
import { formatMoney, formatPercent } from "@/lib/format";
import type { BacktestResponse } from "@/types/domain";

export function BacktestExplorer() {
  const [data, setData] = useState<BacktestResponse | null>(null);
  const [failed, setFailed] = useState(false);
  const [type, setType] = useState<"all" | "official" | "evaluation">("all");

  useEffect(() => {
    let active = true;
    api
      .backtests("limit=100")
      .then((response) => {
        if (active) setData(response);
      })
      .catch(() => {
        if (active) setFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const items =
    data?.items.filter(
      (item) => type === "all" || item.forecast.forecast_type === type,
    ) ?? [];

  return (
    <div className="mx-auto max-w-[1500px] px-5 py-8 sm:px-8 lg:px-10">
      <header className="border-b border-[var(--line)] pb-6">
        <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
          Public model accountability
        </p>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-3xl font-extrabold text-white">Backtests</h1>
            <p className="mt-2 max-w-3xl text-xs leading-5 text-[var(--muted)]">
              Evaluation forecasts and genuinely pre-release official locks are
              labeled separately. SlateSignal never presents a retrospective
              model run as an ex-ante prediction.
            </p>
          </div>
          <div
            className="flex border border-[var(--line)]"
            aria-label="Forecast type"
          >
            {(["all", "official", "evaluation"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => setType(item)}
                className={`h-9 border-r border-[var(--line)] px-3 text-[10px] font-bold uppercase last:border-r-0 ${
                  type === item
                    ? "bg-[var(--signal)] text-black"
                    : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </div>
      </header>

      {!data && !failed ? (
        <div className="grid h-72 place-items-center">
          <LoaderCircle
            size={20}
            className="animate-spin text-[var(--muted)]"
          />
        </div>
      ) : failed ? (
        <div className="flex items-center gap-3 py-16 text-sm text-[var(--warning)]">
          <CircleAlert size={18} />
          Backtest data is unavailable.
        </div>
      ) : data ? (
        <>
          <section className="grid border-x border-b border-[var(--line)] sm:grid-cols-4">
            <BacktestMetric
              icon={<Target size={15} />}
              label="Scored films"
              value={String(data.metrics.count)}
              detail="sealed forecast runs"
            />
            <BacktestMetric
              icon={<BarChart3 size={15} />}
              label="Dollar MAE"
              value={
                data.metrics.mae !== null
                  ? formatMoney(data.metrics.mae, 1)
                  : "Pending"
              }
              detail="mean absolute error"
            />
            <BacktestMetric
              icon={<Gauge size={15} />}
              label="Log MAE"
              value={
                data.metrics.log_mae !== null
                  ? data.metrics.log_mae.toFixed(3)
                  : "Pending"
              }
              detail="scale-normalized error"
            />
            <BacktestMetric
              icon={<Target size={15} />}
              label="80% coverage"
              value={
                data.metrics.interval_coverage !== null
                  ? formatPercent(data.metrics.interval_coverage)
                  : "Pending"
              }
              detail="empirical interval coverage"
            />
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-extrabold text-white">
              Film-level scorecard
            </h2>
            <div className="mt-4 overflow-x-auto border-t border-[var(--line)]">
              <table className="w-full min-w-[940px] border-collapse text-left">
                <thead>
                  <tr className="border-b border-[var(--line)] text-[9px] font-bold text-[var(--muted)] uppercase">
                    <th className="py-3 pr-4">Film</th>
                    <th className="px-4 py-3">Cutoff / type</th>
                    <th className="px-4 py-3 text-right">P10</th>
                    <th className="px-4 py-3 text-right">P50</th>
                    <th className="px-4 py-3 text-right">P90</th>
                    <th className="px-4 py-3 text-right">Actual</th>
                    <th className="py-3 pl-4 text-right">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const interval = item.forecast.worldwide;
                    return (
                      <tr
                        key={item.forecast.forecast_id}
                        className="border-b border-[var(--line)] text-xs"
                      >
                        <td className="py-3 pr-4">
                          <Link
                            href={`/movies/${item.movie.slug}`}
                            className="font-bold text-white hover:text-[var(--signal)]"
                          >
                            {item.movie.title}
                          </Link>
                          <p className="mt-1 text-[9px] text-[var(--muted)]">
                            {item.movie.release_year} ·{" "}
                            {item.forecast.model_version}
                          </p>
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-[10px] text-[var(--muted-strong)]">
                            {new Date(
                              item.forecast.data_cutoff,
                            ).toLocaleDateString()}
                          </p>
                          <p
                            className={`mt-1 text-[8px] font-bold uppercase ${
                              item.forecast.forecast_type === "official"
                                ? "text-[var(--positive)]"
                                : "text-[var(--warning)]"
                            }`}
                          >
                            {item.forecast.forecast_type}
                          </p>
                        </td>
                        <MoneyCell value={interval?.p10 ?? null} />
                        <MoneyCell value={interval?.p50 ?? null} strong />
                        <MoneyCell value={interval?.p90 ?? null} />
                        <MoneyCell
                          value={item.actual_worldwide?.amount ?? null}
                          strong
                        />
                        <td className="py-3 pl-4 text-right">
                          <p className="tabular font-bold text-white">
                            {item.absolute_error !== null
                              ? formatMoney(item.absolute_error, 0)
                              : "N/A"}
                          </p>
                          <p className="tabular mt-1 text-[9px] text-[var(--muted)]">
                            {item.absolute_percentage_error !== null
                              ? formatPercent(item.absolute_percentage_error)
                              : ""}
                          </p>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              {!items.length && (
                <p className="border-b border-[var(--line)] py-14 text-center text-xs text-[var(--muted)]">
                  No sealed forecasts match this type yet.
                </p>
              )}
            </div>
          </section>

          <p className="mt-6 max-w-4xl text-[10px] leading-4 text-[var(--muted)]">
            {data.methodology_note}
          </p>
        </>
      ) : null}
    </div>
  );
}

function BacktestMetric({
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
    <div className="border-b border-[var(--line)] p-4 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0">
      <div className="flex items-center gap-2 text-[var(--muted)]">
        {icon}
        <span className="text-[9px] font-bold uppercase">{label}</span>
      </div>
      <p className="tabular mt-2 text-2xl font-extrabold text-white">{value}</p>
      <p className="mt-1 text-[10px] text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function MoneyCell({
  value,
  strong = false,
}: {
  value: number | null;
  strong?: boolean;
}) {
  return (
    <td
      className={`tabular px-4 py-3 text-right ${
        strong ? "font-extrabold text-white" : "text-[var(--muted-strong)]"
      }`}
    >
      {value !== null ? formatMoney(value, 0) : "N/A"}
    </td>
  );
}
