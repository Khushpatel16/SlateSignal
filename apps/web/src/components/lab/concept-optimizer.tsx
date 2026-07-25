"use client";

import { useState } from "react";
import {
  ArrowRight,
  BookmarkPlus,
  CalendarDays,
  CircleAlert,
  Film,
  LoaderCircle,
  Sparkles,
  UsersRound,
} from "lucide-react";
import { toast } from "sonner";

import { SliderField } from "@/components/lab/slider-field";
import { api, ApiError } from "@/lib/api";
import {
  classNames,
  formatDate,
  formatMoney,
  formatPercent,
} from "@/lib/format";
import type {
  ForecastRequest,
  OptimizeRequest,
  OptimizeResponse,
  PlanRecommendation,
} from "@/types/domain";

export function ConceptOptimizer({
  seed,
  onUsePlan,
}: {
  seed: ForecastRequest;
  onUsePlan: (request: ForecastRequest) => void;
}) {
  const [targetBudget, setTargetBudget] = useState(seed.budget);
  const [earliest, setEarliest] = useState("2027-01-01");
  const [latest, setLatest] = useState("2028-12-31");
  const [fixedDirector, setFixedDirector] = useState("");
  const [fixedCast, setFixedCast] = useState("");
  const [risk, setRisk] =
    useState<OptimizeRequest["risk_tolerance"]>("balanced");
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function optimize() {
    if (seed.synopsis.length < 80) {
      setError("Add at least 80 characters of synopsis before optimizing.");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const response = await api.optimize({
        title: seed.title || "Untitled project",
        synopsis: seed.synopsis,
        genres: seed.genres,
        target_budget: targetBudget,
        earliest_release: earliest,
        latest_release: latest,
        fixed_director: fixedDirector.trim() || null,
        fixed_cast: fixedCast
          .split(",")
          .map((name) => name.trim())
          .filter(Boolean)
          .slice(0, 4),
        risk_tolerance: risk,
      });
      setResult(response);
    } catch {
      setError("The optimizer service is temporarily offline.");
    } finally {
      setPending(false);
    }
  }

  async function saveStrategies() {
    if (!result) return;
    try {
      await api.saveProject({
        title: `${seed.title} - strategy set`,
        project_type: "optimization",
        payload: {
          seed,
          optimization: result,
        },
      });
      toast.success("Strategy set saved");
    } catch (saveError) {
      if (saveError instanceof ApiError && saveError.status === 401) {
        toast.error("Sign in to save this strategy set", {
          action: {
            label: "Sign in",
            onClick: () => {
              window.location.href = "/login";
            },
          },
        });
      } else {
        toast.error("Could not save this strategy set");
      }
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-var(--topbar))] xl:grid-cols-[390px_minmax(0,1fr)]">
      <aside className="border-b border-[var(--line)] bg-[var(--canvas-raised)] xl:border-r xl:border-b-0">
        <div className="border-b border-[var(--line)] p-5">
          <div className="flex items-center gap-2 text-[var(--signal)]">
            <Sparkles size={16} />
            <p className="text-[10px] font-bold uppercase">Concept optimizer</p>
          </div>
          <h2 className="font-editorial mt-2 text-2xl font-semibold text-white">
            Build the most robust package
          </h2>
          <p className="mt-2 text-xs leading-5 text-[var(--muted)]">
            Three package paths ranked across historical fit, release windows,
            expected value, and downside resilience.
          </p>
        </div>

        <div className="space-y-6 p-5">
          <div>
            <p className="text-xs font-bold text-white">{seed.title}</p>
            <p className="mt-1 line-clamp-3 text-[11px] leading-5 text-[var(--muted)]">
              {seed.synopsis}
            </p>
            <p className="mt-2 text-[10px] font-bold text-[var(--signal)]">
              {seed.genres.join(" · ")}
            </p>
          </div>

          <SliderField
            label="Target production budget"
            value={targetBudget}
            min={1_000_000}
            max={250_000_000}
            step={1_000_000}
            format="money"
            onChange={setTargetBudget}
          />

          <div className="grid grid-cols-2 gap-3">
            <DateField
              label="Earliest"
              value={earliest}
              onChange={setEarliest}
            />
            <DateField label="Latest" value={latest} onChange={setLatest} />
          </div>

          <label className="block">
            <span className="text-xs font-bold text-[var(--muted-strong)]">
              Lock a director
            </span>
            <input
              value={fixedDirector}
              onChange={(event) => setFixedDirector(event.target.value)}
              placeholder="Optional"
              className="mt-2 h-10 w-full border border-[var(--line)] bg-[var(--canvas)] px-3 text-xs text-white placeholder:text-[#666] focus:border-[var(--signal)] focus:outline-none"
            />
          </label>

          <label className="block">
            <span className="text-xs font-bold text-[var(--muted-strong)]">
              Lock cast choices
            </span>
            <input
              value={fixedCast}
              onChange={(event) => setFixedCast(event.target.value)}
              placeholder="Comma-separated, optional"
              className="mt-2 h-10 w-full border border-[var(--line)] bg-[var(--canvas)] px-3 text-xs text-white placeholder:text-[#666] focus:border-[var(--signal)] focus:outline-none"
            />
          </label>

          <div>
            <p className="text-xs font-bold text-[var(--muted-strong)]">
              Risk posture
            </p>
            <div className="mt-2 grid grid-cols-3 border border-[var(--line)]">
              {(["conservative", "balanced", "aggressive"] as const).map(
                (option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setRisk(option)}
                    className={classNames(
                      "h-9 border-r border-[var(--line)] text-[10px] font-bold capitalize last:border-r-0",
                      risk === option
                        ? "bg-[var(--signal)] text-black"
                        : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
                    )}
                  >
                    {option}
                  </button>
                ),
              )}
            </div>
          </div>

          {error && (
            <p className="flex items-start gap-2 text-xs leading-5 text-[var(--negative)]">
              <CircleAlert size={15} className="mt-0.5 shrink-0" />
              {error}
            </p>
          )}

          <button
            type="button"
            onClick={optimize}
            disabled={pending}
            className="flex h-11 w-full items-center justify-center gap-2 bg-[var(--signal)] text-sm font-extrabold text-black hover:bg-[var(--signal-strong)] disabled:cursor-wait disabled:opacity-70"
          >
            {pending ? (
              <LoaderCircle size={17} className="animate-spin" />
            ) : (
              <Sparkles size={17} />
            )}
            Generate three strategies
          </button>
        </div>
      </aside>

      <section className="min-w-0 p-5 sm:p-7 lg:p-9">
        {result ? (
          <>
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
                  Optimized package set
                </p>
                <h2 className="font-editorial mt-1 text-3xl font-semibold text-white">
                  Three ways to greenlight {seed.title}
                </h2>
              </div>
              <p className="max-w-xl text-xs leading-5 text-[var(--muted)]">
                Suggested names reflect historical fit, not availability,
                endorsement, or a hiring decision.
              </p>
              <button
                type="button"
                onClick={saveStrategies}
                className="flex h-9 items-center gap-2 border border-[var(--line)] px-3 text-xs font-bold text-[var(--muted-strong)] hover:bg-[var(--surface)] hover:text-white"
              >
                <BookmarkPlus size={14} />
                Save strategies
              </button>
            </div>

            <div className="mt-7 grid gap-4 lg:grid-cols-3">
              {result.plans.map((plan) => (
                <PlanCard
                  key={plan.id}
                  plan={plan}
                  recommended={
                    (risk === "conservative" && plan.id === "precision") ||
                    (risk === "balanced" && plan.id === "balanced") ||
                    (risk === "aggressive" && plan.id === "event")
                  }
                  onUse={() => onUsePlan(plan.request)}
                />
              ))}
            </div>

            <div className="mt-6 border-l-2 border-[var(--signal)] bg-[var(--surface)] p-4">
              <p className="text-sm font-bold text-white">Decision readout</p>
              <p className="mt-1 text-xs leading-5 text-[var(--muted)]">
                {result.recommendation}
              </p>
            </div>
          </>
        ) : (
          <div className="grid min-h-[600px] place-items-center">
            <div className="max-w-md text-center">
              <span className="mx-auto grid size-12 place-items-center border border-[var(--line)] bg-[var(--surface)] text-[var(--signal)]">
                <Film size={22} />
              </span>
              <h2 className="font-editorial mt-5 text-3xl font-semibold text-white">
                Your three production paths will appear here
              </h2>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                Set your budget, timeline, and any locked talent. The optimizer
                will trade expected gross against profitability and robustness.
              </p>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}

function PlanCard({
  plan,
  recommended,
  onUse,
}: {
  plan: PlanRecommendation;
  recommended: boolean;
  onUse: () => void;
}) {
  const forecast = plan.forecast;
  return (
    <article
      className={classNames(
        "relative border bg-[var(--surface)]",
        recommended ? "border-[var(--signal)]" : "border-[var(--line)]",
      )}
    >
      {recommended && (
        <span className="absolute top-3 right-3 bg-[var(--signal)] px-2 py-1 text-[9px] font-extrabold text-black uppercase">
          Best fit
        </span>
      )}
      <div className="border-b border-[var(--line)] p-4 pr-20">
        <p className="text-[10px] font-bold text-[var(--muted)] uppercase">
          {plan.id}
        </p>
        <h3 className="mt-1 text-lg font-extrabold text-white">{plan.label}</h3>
        <p className="mt-2 min-h-10 text-[11px] leading-5 text-[var(--muted)]">
          {plan.thesis}
        </p>
      </div>
      <div className="p-4">
        <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
          Expected worldwide
        </p>
        <p className="tabular mt-1 text-3xl font-extrabold text-white">
          {formatMoney(forecast.financials.worldwide_gross.expected)}
        </p>
        <p className="tabular mt-1 text-[10px] text-[var(--muted)]">
          {formatMoney(forecast.financials.worldwide_gross.low)}–
          {formatMoney(forecast.financials.worldwide_gross.high)}
        </p>

        <div className="mt-5 space-y-3 border-t border-[var(--line)] pt-4">
          <PlanRow
            icon={<UsersRound size={13} />}
            label="Director"
            value={plan.request.director ?? "Open"}
          />
          <PlanRow
            icon={<Film size={13} />}
            label="Studio"
            value={plan.request.studio ?? "Open"}
          />
          <PlanRow
            icon={<CalendarDays size={13} />}
            label="Release"
            value={formatDate(plan.request.release_date)}
          />
          <PlanRow label="Budget" value={formatMoney(plan.request.budget)} />
          <PlanRow
            label="Break-even"
            value={formatPercent(forecast.financials.break_even_probability)}
          />
          <PlanRow
            label="Robustness"
            value={`${forecast.robustness.score} · ${forecast.robustness.label}`}
          />
        </div>

        <button
          type="button"
          onClick={onUse}
          className="mt-5 flex h-10 w-full items-center justify-center gap-2 border border-[var(--line)] text-xs font-bold text-white hover:bg-[var(--surface-soft)]"
        >
          Load into forecast
          <ArrowRight size={14} />
        </button>
      </div>
    </article>
  );
}

function PlanRow({
  icon,
  label,
  value,
}: {
  icon?: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start justify-between gap-3 text-[11px]">
      <span className="flex items-center gap-1.5 text-[var(--muted)]">
        {icon}
        {label}
      </span>
      <span className="max-w-[58%] text-right font-bold text-white">
        {value}
      </span>
    </div>
  );
}

function DateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label>
      <span className="text-xs font-bold text-[var(--muted-strong)]">
        {label}
      </span>
      <input
        type="date"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-2 h-10 w-full border border-[var(--line)] bg-[var(--canvas)] px-2 text-[11px] text-white focus:border-[var(--signal)] focus:outline-none"
      />
    </label>
  );
}
