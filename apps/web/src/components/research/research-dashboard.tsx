"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Database,
  FileDigit,
  GitCompareArrows,
  Network,
  ShieldCheck,
} from "lucide-react";

import { formatPercent } from "@/lib/format";
import research from "@/lib/research-results.json";

const periods = [
  {
    period: "2024 validation",
    original: research.periods["2024_validation"].original.mae_usd / 1_000_000,
    corrected:
      research.periods["2024_validation"].corrected.mae_usd / 1_000_000,
  },
  {
    period: "2025 holdout",
    original:
      research.periods["2025_closed_holdout"].original.mae_usd / 1_000_000,
    corrected:
      research.periods["2025_closed_holdout"].corrected.mae_usd / 1_000_000,
  },
];

const baselineComparison = [
  { model: "Structured XGB", mae: 141.21, fill: "#8f8d87" },
  { model: "TF-IDF + XGB", mae: 128.99, fill: "#78aee8" },
  { model: "BERT + XGB", mae: 115.03, fill: "#f0c94c" },
  { model: "Corrected 2024", mae: 104.22, fill: "#68c6a3" },
];

const budgetError = [
  { segment: "Micro", error: 8.6 },
  { segment: "Low", error: 17.1 },
  { segment: "Mid", error: 46.8 },
  { segment: "High", error: 117.4 },
  { segment: "Blockbuster", error: 253.4 },
];

const architecture = [
  {
    step: "01",
    title: "Synopsis",
    detail: "bert-base-uncased · 512 tokens",
    icon: FileDigit,
  },
  {
    step: "02",
    title: "Mean pooling",
    detail: "768-dimensional attention-masked vector",
    icon: Network,
  },
  {
    step: "03",
    title: "Structured context",
    detail: "Time-frozen package and release factors",
    icon: Database,
  },
  {
    step: "04",
    title: "XGBoost",
    detail: "Log worldwide gross with conformal bounds",
    icon: GitCompareArrows,
  },
];

export function ResearchDashboard() {
  const gates = Object.entries(research.promotion_gates);
  return (
    <div>
      <header className="border-b border-[var(--line)] bg-[var(--canvas-raised)]">
        <div className="mx-auto max-w-[1500px] px-5 py-9 sm:px-8 lg:px-10">
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            SlateSignal research
          </p>
          <h1 className="mt-3 max-w-5xl text-3xl leading-tight font-extrabold text-white sm:text-5xl">
            Bias-Aware Financial Success Prediction for Film Productions Using
            Multi-Modal NLP
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-6 text-[var(--muted)]">
            An honest reconstruction of the original 6,437-film study, its
            BERT-XGBoost baseline, the defects discovered during
            productionization, and the time-frozen successor tournament.
          </p>
        </div>
      </header>

      <section className="border-b border-[var(--line)]">
        <div className="mx-auto grid max-w-[1500px] sm:grid-cols-4 sm:px-8 lg:px-10">
          <ResearchMetric
            label="Real films"
            value="6,437"
            detail="1970-2025 corpus"
          />
          <ResearchMetric
            label="BERT dimensions"
            value="768"
            detail="mean-pooled encoder"
          />
          <ResearchMetric
            label="2024 corrected MAE"
            value="$104.2M"
            detail="vs $111.1M original"
          />
          <ResearchMetric
            label="Promotion"
            value="Blocked"
            detail="coverage + fairness gates"
            warning
          />
        </div>
      </section>

      <div className="mx-auto max-w-[1500px] px-5 py-10 sm:px-8 lg:px-10">
        <section>
          <SectionHeading
            eyebrow="Architecture"
            title="From synopsis to interval"
            detail="The original serving contract is preserved exactly: 15 structured features plus a 768-dimensional mean-pooled BERT embedding."
          />
          <div className="mt-6 grid gap-px border border-[var(--line)] bg-[var(--line)] lg:grid-cols-4">
            {architecture.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.step} className="bg-[var(--canvas)] p-5">
                  <div className="flex items-center justify-between">
                    <Icon size={18} className="text-[var(--signal)]" />
                    <span className="font-mono text-[9px] text-[var(--muted)]">
                      {item.step}
                    </span>
                  </div>
                  <h3 className="mt-6 text-sm font-extrabold text-white">
                    {item.title}
                  </h3>
                  <p className="mt-2 text-[10px] leading-4 text-[var(--muted)]">
                    {item.detail}
                  </p>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-2 font-mono text-[9px] text-[var(--muted)]">
            <span className="border border-[var(--line)] px-2 py-1">
              max_length=512
            </span>
            <ArrowRight size={12} />
            <span className="border border-[var(--line)] px-2 py-1">
              pooling=attention_mask_mean
            </span>
            <ArrowRight size={12} />
            <span className="border border-[var(--line)] px-2 py-1">
              features=783
            </span>
            <ArrowRight size={12} />
            <span className="border border-[var(--line)] px-2 py-1">
              target=log1p(worldwide_usd)
            </span>
          </div>
        </section>

        <section className="mt-14">
          <SectionHeading
            eyebrow="Model tournament"
            title="Temporal performance"
            detail="Hyperparameters were selected on 2022-2023. The model was then retrained through 2023, calibrated on 2024, and evaluated on 24 closed 2025 holdout films."
          />
          <div className="mt-6 grid gap-8 xl:grid-cols-2">
            <ChartPanel
              title="Dollar MAE by temporal split"
              unit="USD millions"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={periods}
                  margin={{ top: 12, right: 8, left: 0 }}
                >
                  <CartesianGrid
                    stroke="#29292d"
                    vertical={false}
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    dataKey="period"
                    tick={{ fill: "#8f8d87", fontSize: 10 }}
                    axisLine={{ stroke: "#39393d" }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(value) => `$${value}M`}
                    tick={{ fill: "#8f8d87", fontSize: 9 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <ChartTooltip
                    contentStyle={tooltipStyle}
                    formatter={(value) => `$${Number(value).toFixed(1)}M`}
                  />
                  <Legend wrapperStyle={{ fontSize: 10, color: "#a5a39c" }} />
                  <Bar dataKey="original" fill="#8f8d87" name="bert-xgb-v1" />
                  <Bar
                    dataKey="corrected"
                    fill="#68c6a3"
                    name="multimodal-xgb-v2"
                  />
                </BarChart>
              </ResponsiveContainer>
            </ChartPanel>
            <ChartPanel
              title="Research baseline progression"
              unit="Lower is better"
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={baselineComparison}
                  layout="vertical"
                  margin={{ left: 18, right: 12 }}
                >
                  <CartesianGrid
                    stroke="#29292d"
                    horizontal={false}
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    type="number"
                    tickFormatter={(value) => `$${value}M`}
                    tick={{ fill: "#8f8d87", fontSize: 9 }}
                    axisLine={{ stroke: "#39393d" }}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="model"
                    width={105}
                    tick={{ fill: "#c9c6bd", fontSize: 9 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <ChartTooltip
                    contentStyle={tooltipStyle}
                    formatter={(value) => `$${Number(value).toFixed(2)}M`}
                  />
                  <Bar dataKey="mae">
                    {baselineComparison.map((entry) => (
                      <Cell key={entry.model} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartPanel>
          </div>
        </section>

        <section className="mt-14 grid gap-8 xl:grid-cols-[minmax(0,1fr)_390px]">
          <div>
            <SectionHeading
              eyebrow="Error analysis"
              title="Budget is still the hard axis"
              detail="The original baseline's absolute error expands sharply with production scale. This is why SlateSignal reports intervals and budget segments, not a single confident number."
            />
            <div className="mt-6 h-80 border-y border-[var(--line)] py-4">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={budgetError}>
                  <CartesianGrid
                    stroke="#29292d"
                    vertical={false}
                    strokeDasharray="3 3"
                  />
                  <XAxis
                    dataKey="segment"
                    tick={{ fill: "#8f8d87", fontSize: 10 }}
                    axisLine={{ stroke: "#39393d" }}
                    tickLine={false}
                  />
                  <YAxis
                    tickFormatter={(value) => `$${value}M`}
                    tick={{ fill: "#8f8d87", fontSize: 9 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <ChartTooltip
                    contentStyle={tooltipStyle}
                    formatter={(value) => `$${Number(value).toFixed(1)}M`}
                  />
                  <Bar dataKey="error" fill="#ef746b" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          <aside className="border border-[var(--line)] bg-[var(--surface)] p-5">
            <div className="flex items-center gap-2">
              <ShieldCheck size={17} className="text-[var(--signal)]" />
              <h2 className="text-sm font-extrabold text-white">
                Promotion gates
              </h2>
            </div>
            <p className="mt-3 text-[10px] leading-4 text-[var(--muted)]">
              A better point estimate is not sufficient for production
              promotion.
            </p>
            <div className="mt-4 border-t border-[var(--line)]">
              {gates.map(([key, passed]) => (
                <div
                  key={key}
                  className="flex items-start gap-3 border-b border-[var(--line)] py-3"
                >
                  {passed ? (
                    <CheckCircle2
                      size={15}
                      className="mt-0.5 shrink-0 text-[var(--positive)]"
                    />
                  ) : (
                    <CircleAlert
                      size={15}
                      className="mt-0.5 shrink-0 text-[var(--warning)]"
                    />
                  )}
                  <div>
                    <p className="text-[10px] font-bold text-white">
                      {key.replaceAll("_", " ")}
                    </p>
                    <p className="mt-1 text-[9px] text-[var(--muted)]">
                      {passed ? "Passed" : "Not yet satisfied"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[10px] leading-4 text-[var(--muted)]">
              The corrected candidate improves temporal log-MAE and dollar MAE,
              but 2025 interval coverage is{" "}
              {formatPercent(research.conformal_holdout_coverage)} and the
              Wikidata-backed matched-cohort fairness audit is not yet
              sufficiently powered. It is not promoted.
            </p>
          </aside>
        </section>

        <section className="mt-14 border-y border-[var(--line)] py-8">
          <SectionHeading
            eyebrow="Fairness"
            title="Bias-aware, not bias-free"
            detail="Gender and other protected attributes are excluded from model inputs. Demographic annotations are permitted only for evaluation against matched budget, genre, and year cohorts."
          />
          <div className="mt-6 grid gap-px bg-[var(--line)] md:grid-cols-3">
            <FairnessItem
              title="Input policy"
              detail="No gender, race, ethnicity, age, or inferred protected identity is scored."
              status="Pass"
            />
            <FairnessItem
              title="Proxy risk"
              detail="Track record can encode unequal historical opportunity, so group-normalized error stays under review."
              status="Watch"
            />
            <FairnessItem
              title="Evidence policy"
              detail="The original name-based binary gender analysis is retained as history but rejected as production evidence."
              status="Corrected"
            />
          </div>
        </section>

        <section className="mt-14">
          <SectionHeading
            eyebrow="Defect register"
            title="What changed for production"
            detail="Productionization surfaced errors that a polished chart alone could not."
          />
          <div className="mt-5 grid border-t border-[var(--line)] md:grid-cols-2">
            {[
              "Stale test CSV and embedding alignment is blocked by row and feature checksums.",
              "CLS inference was replaced with the training-time attention-masked mean pool.",
              "Early stopping now uses an internal temporal fold, never the final holdout.",
              "Post-release social signals and hand-authored revenue multipliers were removed.",
              "Historical budgets and grosses are CPI-normalized before corrected training.",
              "The budget-confounded binary gender comparison no longer supports fairness claims.",
            ].map((item) => (
              <div
                key={item}
                className="border-b border-[var(--line)] py-4 text-xs leading-5 text-[var(--muted-strong)] md:odd:pr-6 md:even:border-l md:even:pl-6"
              >
                {item}
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

const tooltipStyle = {
  background: "#171719",
  border: "1px solid #303034",
  borderRadius: 0,
  fontSize: 11,
};

function SectionHeading({
  eyebrow,
  title,
  detail,
}: {
  eyebrow: string;
  title: string;
  detail: string;
}) {
  return (
    <div>
      <p className="text-[9px] font-bold text-[var(--signal)] uppercase">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-2xl font-extrabold text-white">{title}</h2>
      <p className="mt-2 max-w-3xl text-xs leading-5 text-[var(--muted)]">
        {detail}
      </p>
    </div>
  );
}

function ResearchMetric({
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
    <div className="border-b border-[var(--line)] px-5 py-5 last:border-b-0 sm:border-r sm:border-b-0 sm:px-5 sm:first:pl-0 sm:last:border-r-0">
      <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
        {label}
      </p>
      <p
        className={`tabular mt-2 text-2xl font-extrabold ${
          warning ? "text-[var(--warning)]" : "text-white"
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-[10px] text-[var(--muted)]">{detail}</p>
    </div>
  );
}

function ChartPanel({
  title,
  unit,
  children,
}: {
  title: string;
  unit: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex items-end justify-between border-b border-[var(--line)] pb-3">
        <h3 className="text-sm font-extrabold text-white">{title}</h3>
        <p className="text-[9px] text-[var(--muted)]">{unit}</p>
      </div>
      <div className="h-72 pt-4">{children}</div>
    </div>
  );
}

function FairnessItem({
  title,
  detail,
  status,
}: {
  title: string;
  detail: string;
  status: string;
}) {
  return (
    <div className="bg-[var(--canvas)] p-5">
      <p className="text-[9px] font-bold text-[var(--signal)] uppercase">
        {status}
      </p>
      <h3 className="mt-2 text-sm font-extrabold text-white">{title}</h3>
      <p className="mt-2 text-[10px] leading-4 text-[var(--muted)]">{detail}</p>
    </div>
  );
}
