"use client";

import Link from "next/link";
import {
  BookmarkPlus,
  Check,
  ChevronRight,
  CircleAlert,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";

import { FactorChart } from "@/components/charts/factor-chart";
import { api, ApiError } from "@/lib/api";
import { formatMoney, formatPercent } from "@/lib/format";
import type { ForecastRequest, ForecastResponse } from "@/types/domain";

export function ForecastResults({
  result,
  pending,
  error,
  request,
}: {
  result: ForecastResponse | null;
  pending: boolean;
  error: string | null;
  request: ForecastRequest;
}) {
  async function save() {
    if (!result) return;
    try {
      await api.saveProject({
        title: `${request.title} - ${request.release_date}`,
        project_type: "forecast",
        payload: {
          input: request,
          forecast: result,
        },
      });
      toast.success("Forecast saved");
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 401) {
        toast.error("Sign in to save this forecast", {
          action: {
            label: "Sign in",
            onClick: () => {
              window.location.href = "/login";
            },
          },
        });
      } else {
        toast.error("Could not save this forecast");
      }
    }
  }

  if (!result) {
    return (
      <div className="grid min-h-[620px] place-items-center p-8">
        <div className="max-w-sm text-center">
          {error ? (
            <CircleAlert size={28} className="mx-auto text-[var(--warning)]" />
          ) : (
            <LoaderCircle
              size={28}
              className="mx-auto animate-spin text-[var(--signal)]"
            />
          )}
          <h2 className="mt-4 text-lg font-bold text-white">
            {error ? "Forecast engine unavailable" : "Building your forecast"}
          </h2>
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
            {error ??
              "Calibrating the package against 6,437 historical films and 600 market scenarios."}
          </p>
        </div>
      </div>
    );
  }

  const gross = result.financials.worldwide_gross;
  const rangeSpan = gross.high - gross.low;
  const expectedPosition =
    rangeSpan > 0 ? ((gross.expected - gross.low) / rangeSpan) * 100 : 50;
  const topFactors = [...result.factors]
    .filter((factor) => factor.key !== "budget")
    .sort((a, b) => Math.abs(b.impact) - Math.abs(a.impact))
    .slice(0, 5);

  return (
    <div className="relative">
      <div
        className={`pointer-events-none absolute inset-x-0 top-0 z-10 h-0.5 bg-[var(--signal)] transition-opacity ${
          pending ? "opacity-100" : "opacity-0"
        }`}
      />

      <section className="border-b border-[var(--line)] p-5 sm:p-7">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="size-2 bg-[var(--positive)]" />
              <p className="text-[10px] font-bold text-[var(--muted)] uppercase">
                Live scenario · {result.model_version}
              </p>
            </div>
            <h2 className="font-editorial mt-3 text-3xl font-semibold text-white sm:text-4xl">
              {request.title || "Untitled project"}
            </h2>
          </div>
          <button
            type="button"
            onClick={save}
            className="flex h-9 items-center gap-2 border border-[var(--line)] px-3 text-xs font-bold text-[var(--muted-strong)] hover:bg-[var(--surface-soft)] hover:text-white"
          >
            <BookmarkPlus size={15} />
            Save analysis
          </button>
        </div>

        <div className="mt-7 grid gap-5 sm:grid-cols-[1.4fr_1fr]">
          <div>
            <p className="text-[10px] font-bold text-[var(--muted)] uppercase">
              Expected worldwide gross
            </p>
            <p className="tabular mt-1 text-5xl font-extrabold text-white sm:text-6xl">
              {formatMoney(gross.expected)}
            </p>
            <div className="mt-5">
              <div className="relative h-2 bg-[var(--surface-soft)]">
                <div className="absolute inset-0 bg-[var(--info)] opacity-45" />
                <span
                  className="absolute top-1/2 size-4 -translate-x-1/2 -translate-y-1/2 border-2 border-black bg-[var(--signal)]"
                  style={{ left: `${expectedPosition}%` }}
                />
              </div>
              <div className="tabular mt-2 flex justify-between text-[10px] text-[var(--muted)]">
                <span>{formatMoney(gross.low)} downside</span>
                <span>{formatMoney(gross.high)} upside</span>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-2 border border-[var(--line)]">
            <Metric
              label="Break-even chance"
              value={formatPercent(result.financials.break_even_probability)}
            />
            <Metric
              label="Expected ROI"
              value={formatPercent(result.financials.expected_roi)}
              positive={result.financials.expected_roi >= 0}
            />
            <Metric
              label="Opening weekend"
              value={formatMoney(result.financials.opening_weekend.expected)}
            />
            <Metric
              label="Expected profit"
              value={formatMoney(result.financials.expected_profit)}
              positive={result.financials.expected_profit >= 0}
            />
          </div>
        </div>
      </section>

      <section className="grid border-b border-[var(--line)] lg:grid-cols-[1.4fr_1fr]">
        <div className="border-b border-[var(--line)] p-5 sm:p-7 lg:border-r lg:border-b-0">
          <div className="flex items-end justify-between">
            <div>
              <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
                Counterfactual drivers
              </p>
              <h3 className="mt-1 text-lg font-bold text-white">
                What is moving the forecast
              </h3>
            </div>
            <p className="text-[10px] text-[var(--muted)]">USD impact</p>
          </div>
          <div className="mt-4">
            <FactorChart factors={result.factors} />
          </div>
        </div>

        <div className="p-5 sm:p-7">
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            Greenlight Twin
          </p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="tabular text-5xl font-extrabold text-white">
              {result.robustness.score}
            </span>
            <span
              className={`text-sm font-bold ${
                result.robustness.label === "Resilient"
                  ? "text-[var(--positive)]"
                  : result.robustness.label === "Fragile"
                    ? "text-[var(--negative)]"
                    : "text-[var(--warning)]"
              }`}
            >
              {result.robustness.label}
            </span>
          </div>
          <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
            Profitable in{" "}
            <strong className="text-white">
              {formatPercent(result.robustness.profitable_scenarios)}
            </strong>{" "}
            of 600 simulated market and cost conditions.
          </p>
          <div className="mt-5 space-y-3 border-t border-[var(--line)] pt-4">
            <InfoRow
              label="Downside case"
              value={formatMoney(result.robustness.downside_gross)}
            />
            <InfoRow
              label="Upside case"
              value={formatMoney(result.robustness.upside_gross)}
            />
            <InfoRow
              label="Primary fragility"
              value={result.robustness.key_risk}
            />
          </div>
        </div>
      </section>

      <section className="grid border-b border-[var(--line)] xl:grid-cols-2">
        <div className="border-b border-[var(--line)] p-5 sm:p-7 xl:border-r xl:border-b-0">
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            Story signal
          </p>
          <h3 className="mt-1 text-lg font-bold text-white">
            Synopsis diagnostics
          </h3>
          <div className="mt-5 space-y-4">
            {result.synopsis_signals.map((signal) => (
              <div key={signal.label}>
                <div className="flex justify-between gap-3">
                  <span className="text-xs font-bold text-[var(--muted-strong)]">
                    {signal.label}
                  </span>
                  <span className="tabular text-xs font-extrabold text-white">
                    {signal.score}
                  </span>
                </div>
                <div className="mt-2 h-1.5 bg-[var(--surface-soft)]">
                  <div
                    className="h-full bg-[var(--info)]"
                    style={{ width: `${signal.score}%` }}
                  />
                </div>
                <p className="mt-1.5 text-[10px] text-[var(--muted)]">
                  {signal.detail}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="p-5 sm:p-7">
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            Top decisions
          </p>
          <h3 className="mt-1 text-lg font-bold text-white">
            Highest-leverage factors
          </h3>
          <div className="mt-4 border-t border-[var(--line)]">
            {topFactors.map((factor) => (
              <div
                key={factor.key}
                className="flex items-center gap-3 border-b border-[var(--line)] py-3"
              >
                <span
                  className={`grid size-6 shrink-0 place-items-center ${
                    factor.direction === "positive"
                      ? "bg-[rgba(104,198,163,0.12)] text-[var(--positive)]"
                      : factor.direction === "negative"
                        ? "bg-[rgba(239,116,107,0.12)] text-[var(--negative)]"
                        : "bg-[var(--surface-soft)] text-[var(--muted)]"
                  }`}
                >
                  {factor.direction === "positive" ? (
                    <Check size={13} />
                  ) : (
                    <ChevronRight size={13} />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-xs font-bold text-white">
                    {factor.label}
                  </span>
                  <span className="block truncate text-[10px] text-[var(--muted)]">
                    {factor.value}
                  </span>
                </span>
                <span
                  className={`tabular text-xs font-extrabold ${
                    factor.impact > 0
                      ? "text-[var(--positive)]"
                      : factor.impact < 0
                        ? "text-[var(--negative)]"
                        : "text-[var(--muted)]"
                  }`}
                >
                  {factor.impact > 0 ? "+" : ""}
                  {formatMoney(factor.impact)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="p-5 sm:p-7">
        <div className="flex items-start gap-3">
          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0 text-[var(--positive)]"
          />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <h3 className="text-sm font-bold text-white">
                Confidence {result.confidence.score}/100
              </h3>
              <span className="text-[10px] font-bold text-[var(--muted)] uppercase">
                {result.confidence.calibration_segment} budget segment
              </span>
            </div>
            <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
              {result.methodology_note}
            </p>
            <Link
              href="/model-card"
              className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-[var(--signal)] hover:text-[var(--signal-strong)]"
            >
              <Sparkles size={13} />
              Read model evidence and limitations
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function Metric({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean;
}) {
  return (
    <div className="border-r border-b border-[var(--line)] p-3 even:border-r-0 [&:nth-last-child(-n+2)]:border-b-0">
      <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
        {label}
      </p>
      <p
        className={`tabular mt-1 text-lg font-extrabold ${
          positive === undefined
            ? "text-white"
            : positive
              ? "text-[var(--positive)]"
              : "text-[var(--negative)]"
        }`}
      >
        {value}
      </p>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 text-xs">
      <span className="text-[var(--muted)]">{label}</span>
      <span className="max-w-[55%] text-right font-bold text-white">
        {value}
      </span>
    </div>
  );
}
