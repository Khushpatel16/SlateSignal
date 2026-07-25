"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Bookmark,
  CalendarClock,
  CircleAlert,
  Film,
  LoaderCircle,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { api, ApiError } from "@/lib/api";
import { classNames, formatDateTime, formatMoney } from "@/lib/format";
import { stageForecast } from "@/lib/project-transfer";
import type {
  ForecastRequest,
  ForecastResponse,
  SavedProject,
} from "@/types/domain";

export function SavedWorkspace() {
  const router = useRouter();
  const [projects, setProjects] = useState<SavedProject[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [deleteCandidate, setDeleteCandidate] = useState<string | null>(null);
  const [state, setState] = useState<
    "loading" | "ready" | "signed-out" | "error"
  >("loading");

  useEffect(() => {
    let active = true;
    api
      .projects()
      .then((items) => {
        if (!active) return;
        setProjects(items);
        setSelectedId(items[0]?.id ?? null);
        setState("ready");
      })
      .catch((error) => {
        if (!active) return;
        setState(
          error instanceof ApiError && error.status === 401
            ? "signed-out"
            : "error",
        );
      });
    return () => {
      active = false;
    };
  }, []);

  const selected =
    projects.find((project) => project.id === selectedId) ??
    projects[0] ??
    null;
  const request = selected ? readForecastRequest(selected) : null;
  const forecast = selected ? readForecastResponse(selected) : null;

  const projectCounts = useMemo(
    () => ({
      forecasts: projects.filter((item) => item.project_type === "forecast")
        .length,
      optimizations: projects.filter(
        (item) => item.project_type === "optimization",
      ).length,
    }),
    [projects],
  );

  async function remove(project: SavedProject) {
    if (deleteCandidate !== project.id) {
      setDeleteCandidate(project.id);
      return;
    }
    try {
      await api.deleteProject(project.id);
      const next = projects.filter((item) => item.id !== project.id);
      setProjects(next);
      setSelectedId(next[0]?.id ?? null);
      setDeleteCandidate(null);
      toast.success("Saved analysis deleted");
    } catch {
      toast.error("Could not delete this analysis");
    }
  }

  function openInLab() {
    if (!request) return;
    stageForecast(request);
    router.push("/lab");
  }

  if (state === "loading") {
    return (
      <CenteredState
        icon={<LoaderCircle className="animate-spin" />}
        title="Loading saved work"
      />
    );
  }

  if (state === "signed-out") {
    return (
      <CenteredState
        icon={<Bookmark />}
        title="Your decision log starts here"
        detail="Sign in to save forecasts, compare packages, and return to prior assumptions."
        action={
          <Link
            href="/login"
            className="mt-5 inline-flex h-10 items-center gap-2 bg-[var(--signal)] px-4 text-xs font-extrabold text-black"
          >
            Sign in
            <ArrowRight size={15} />
          </Link>
        }
      />
    );
  }

  if (state === "error") {
    return (
      <CenteredState
        icon={<CircleAlert />}
        title="Saved work is unavailable"
        detail="The workspace could not reach the project service."
      />
    );
  }

  return (
    <div className="mx-auto max-w-[1500px] px-5 py-7 sm:px-8 lg:px-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            Decision history
          </p>
          <h1 className="font-editorial mt-1 text-4xl font-semibold text-white">
            Saved work
          </h1>
        </div>
        <Link
          href="/lab"
          className="flex h-10 items-center gap-2 bg-[var(--signal)] px-4 text-xs font-extrabold text-black hover:bg-[var(--signal-strong)]"
        >
          New analysis
          <ArrowRight size={15} />
        </Link>
      </div>

      <div className="mt-7 grid border-y border-[var(--line)] sm:grid-cols-3">
        <LibraryMetric label="Total analyses" value={projects.length} />
        <LibraryMetric label="Forecasts" value={projectCounts.forecasts} />
        <LibraryMetric
          label="Strategy sets"
          value={projectCounts.optimizations}
        />
      </div>

      {projects.length === 0 ? (
        <div className="grid min-h-[440px] place-items-center border-b border-[var(--line)] text-center">
          <div className="max-w-sm">
            <span className="mx-auto grid size-11 place-items-center border border-[var(--line)] text-[var(--signal)]">
              <Bookmark size={19} />
            </span>
            <h2 className="mt-5 text-lg font-bold text-white">
              No saved analyses yet
            </h2>
            <p className="mt-2 text-sm leading-6 text-[var(--muted)]">
              Save a live forecast or an optimizer strategy set to build a
              traceable decision history.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid border-b border-[var(--line)] lg:grid-cols-[minmax(0,0.85fr)_minmax(420px,1.15fr)]">
          <section className="border-b border-[var(--line)] lg:border-r lg:border-b-0">
            {projects.map((project) => (
              <button
                key={project.id}
                type="button"
                onClick={() => {
                  setSelectedId(project.id);
                  setDeleteCandidate(null);
                }}
                className={classNames(
                  "flex w-full items-center gap-3 border-b border-[var(--line)] px-4 py-4 text-left",
                  selected?.id === project.id
                    ? "bg-[var(--surface)]"
                    : "hover:bg-[var(--canvas-raised)]",
                )}
              >
                <span className="grid size-9 shrink-0 place-items-center bg-[var(--surface-soft)] text-[var(--signal)]">
                  {project.project_type === "optimization" ? (
                    <Film size={16} />
                  ) : (
                    <Bookmark size={16} />
                  )}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-bold text-white">
                    {project.title}
                  </span>
                  <span className="mt-1 flex items-center gap-1.5 text-[10px] text-[var(--muted)]">
                    <CalendarClock size={11} />
                    {formatDateTime(project.updated_at)}
                  </span>
                </span>
                <span className="text-[9px] font-bold text-[var(--muted)] uppercase">
                  {project.project_type}
                </span>
              </button>
            ))}
          </section>

          {selected && (
            <section className="min-w-0 p-5 sm:p-7">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
                    {selected.project_type}
                  </p>
                  <h2 className="mt-1 truncate text-xl font-extrabold text-white">
                    {selected.title}
                  </h2>
                  <p className="mt-1 text-[11px] text-[var(--muted)]">
                    Updated {formatDateTime(selected.updated_at)}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => remove(selected)}
                  className={classNames(
                    "flex h-9 items-center gap-2 border px-3 text-xs font-bold",
                    deleteCandidate === selected.id
                      ? "border-[var(--negative)] bg-[rgba(239,116,107,0.1)] text-[var(--negative)]"
                      : "border-[var(--line)] text-[var(--muted)] hover:text-white",
                  )}
                >
                  <Trash2 size={14} />
                  {deleteCandidate === selected.id
                    ? "Confirm delete"
                    : "Delete"}
                </button>
              </div>

              {request ? (
                <>
                  <p className="mt-6 line-clamp-3 text-sm leading-6 text-[var(--muted)]">
                    {request.synopsis}
                  </p>
                  <div className="mt-5 grid grid-cols-2 border border-[var(--line)] sm:grid-cols-4">
                    <Detail
                      label="Budget"
                      value={formatMoney(request.budget)}
                    />
                    <Detail label="Release" value={request.release_date} />
                    <Detail
                      label="Director"
                      value={request.director ?? "Open"}
                    />
                    <Detail
                      label="Expected gross"
                      value={
                        forecast
                          ? formatMoney(
                              forecast.financials.worldwide_gross.expected,
                            )
                          : "Recalculate"
                      }
                    />
                  </div>
                  <div className="mt-5 flex flex-wrap gap-2">
                    {request.genres.map((genre) => (
                      <span
                        key={genre}
                        className="border border-[var(--line)] px-2 py-1 text-[10px] font-bold text-[var(--muted)]"
                      >
                        {genre}
                      </span>
                    ))}
                  </div>
                  <button
                    type="button"
                    onClick={openInLab}
                    className="mt-7 flex h-10 items-center gap-2 bg-[var(--signal)] px-4 text-xs font-extrabold text-black hover:bg-[var(--signal-strong)]"
                  >
                    Open in lab
                    <ArrowRight size={15} />
                  </button>
                </>
              ) : (
                <p className="mt-8 text-sm text-[var(--muted)]">
                  This legacy record does not contain a reusable forecast
                  request.
                </p>
              )}
            </section>
          )}
        </div>
      )}
    </div>
  );
}

function readForecastRequest(project: SavedProject): ForecastRequest | null {
  const direct = project.payload.input ?? project.payload.seed;
  if (isForecastRequest(direct)) return direct;

  const optimization = project.payload.optimization;
  if (
    optimization &&
    typeof optimization === "object" &&
    "plans" in optimization &&
    Array.isArray(optimization.plans)
  ) {
    const firstPlan = optimization.plans[0];
    if (
      firstPlan &&
      typeof firstPlan === "object" &&
      "request" in firstPlan &&
      isForecastRequest(firstPlan.request)
    ) {
      return firstPlan.request;
    }
  }
  return null;
}

function readForecastResponse(project: SavedProject): ForecastResponse | null {
  const value = project.payload.forecast;
  if (
    value &&
    typeof value === "object" &&
    "financials" in value &&
    "robustness" in value
  ) {
    return value as ForecastResponse;
  }
  return null;
}

function isForecastRequest(value: unknown): value is ForecastRequest {
  return Boolean(
    value &&
    typeof value === "object" &&
    "title" in value &&
    "synopsis" in value &&
    "genres" in value &&
    "budget" in value,
  );
}

function LibraryMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="border-b border-[var(--line)] py-4 last:border-b-0 sm:border-r sm:border-b-0 sm:px-5 sm:first:pl-0 sm:last:border-r-0">
      <p className="text-[10px] font-bold text-[var(--muted)] uppercase">
        {label}
      </p>
      <p className="tabular mt-1 text-2xl font-extrabold text-white">{value}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 border-r border-b border-[var(--line)] p-3 even:border-r-0 sm:border-b-0 sm:even:border-r">
      <p className="text-[9px] font-bold text-[var(--muted)] uppercase">
        {label}
      </p>
      <p className="mt-1 truncate text-xs font-bold text-white">{value}</p>
    </div>
  );
}

function CenteredState({
  icon,
  title,
  detail,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  detail?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="grid min-h-[calc(100vh-var(--topbar)-64px)] place-items-center px-5 text-center lg:min-h-[calc(100vh-var(--topbar))]">
      <div className="max-w-sm">
        <span className="mx-auto grid size-11 place-items-center border border-[var(--line)] text-[var(--signal)]">
          {icon}
        </span>
        <h1 className="font-editorial mt-5 text-3xl font-semibold text-white">
          {title}
        </h1>
        {detail && (
          <p className="mt-2 text-sm leading-6 text-[var(--muted)]">{detail}</p>
        )}
        {action}
      </div>
    </div>
  );
}
