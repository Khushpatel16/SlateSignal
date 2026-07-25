"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  Bookmark,
  CircleAlert,
  Film,
  LoaderCircle,
  UsersRound,
} from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { AdminOverview } from "@/types/domain";

export function AdminDashboard() {
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [state, setState] = useState<
    "loading" | "ready" | "signed-out" | "forbidden" | "error"
  >("loading");

  useEffect(() => {
    let active = true;
    api
      .adminOverview()
      .then((result) => {
        if (!active) return;
        setOverview(result);
        setState("ready");
      })
      .catch((error) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 401) {
          setState("signed-out");
        } else if (error instanceof ApiError && error.status === 403) {
          setState("forbidden");
        } else {
          setState("error");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (state === "loading") {
    return (
      <AdminState
        icon={<LoaderCircle className="animate-spin" />}
        title="Loading operations"
      />
    );
  }
  if (state === "signed-out") {
    return (
      <AdminState
        icon={<UsersRound />}
        title="Administrator sign-in required"
        detail="Use the configured administrator account to open this workspace."
        action="/login"
      />
    );
  }
  if (state === "forbidden") {
    return (
      <AdminState
        icon={<CircleAlert />}
        title="Administrator access required"
        detail="This account can use the product but cannot view operations data."
        action="/"
      />
    );
  }
  if (state === "error" || !overview) {
    return (
      <AdminState
        icon={<CircleAlert />}
        title="Operations data unavailable"
        detail="The administration service could not be reached."
      />
    );
  }

  const classified =
    overview.forecast_projects + overview.optimization_projects;
  const forecastShare =
    classified > 0
      ? Math.round((overview.forecast_projects / classified) * 100)
      : 0;

  return (
    <div className="mx-auto max-w-[1500px] px-5 py-7 sm:px-8 lg:px-10">
      <div>
        <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
          Product operations
        </p>
        <h1 className="font-editorial mt-1 text-4xl font-semibold text-white">
          Admin overview
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--muted)]">
          Account, session, and saved-work signals for this deployment.
        </p>
      </div>

      <section className="mt-7 grid border-y border-[var(--line)] sm:grid-cols-2 xl:grid-cols-4">
        <AdminMetric
          label="Accounts"
          value={overview.users}
          icon={<UsersRound size={16} />}
        />
        <AdminMetric
          label="Active sessions"
          value={overview.active_sessions}
          icon={<Activity size={16} />}
        />
        <AdminMetric
          label="Saved analyses"
          value={overview.saved_projects}
          icon={<Bookmark size={16} />}
        />
        <AdminMetric
          label="Strategy sets"
          value={overview.optimization_projects}
          icon={<Film size={16} />}
        />
      </section>

      <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
        <section>
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
                Activity
              </p>
              <h2 className="mt-1 text-xl font-bold text-white">
                Recent saved work
              </h2>
            </div>
            <span className="text-[10px] text-[var(--muted)]">
              Latest eight records
            </span>
          </div>

          <div className="mt-4 overflow-x-auto border-t border-[var(--line)]">
            <table className="w-full min-w-[620px] border-collapse text-left">
              <thead>
                <tr className="border-b border-[var(--line)] text-[9px] font-bold text-[var(--muted)] uppercase">
                  <th className="px-3 py-3">Analysis</th>
                  <th className="px-3 py-3">Owner</th>
                  <th className="px-3 py-3">Type</th>
                  <th className="px-3 py-3">Updated</th>
                </tr>
              </thead>
              <tbody>
                {overview.recent_projects.map((project) => (
                  <tr
                    key={project.id}
                    className="border-b border-[var(--line)] text-xs"
                  >
                    <td className="max-w-64 truncate px-3 py-3 font-bold text-white">
                      {project.title}
                    </td>
                    <td className="px-3 py-3 text-[var(--muted)]">
                      {project.owner_name}
                    </td>
                    <td className="px-3 py-3 text-[var(--muted)]">
                      {project.project_type}
                    </td>
                    <td className="px-3 py-3 text-[var(--muted)]">
                      {formatDateTime(project.updated_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {overview.recent_projects.length === 0 && (
              <p className="border-b border-[var(--line)] px-3 py-12 text-center text-xs text-[var(--muted)]">
                No saved work has been created.
              </p>
            )}
          </div>
        </section>

        <section>
          <p className="text-[10px] font-bold text-[var(--signal)] uppercase">
            Workspace mix
          </p>
          <h2 className="mt-1 text-xl font-bold text-white">Analysis types</h2>
          <div className="mt-5 border border-[var(--line)] bg-[var(--surface)] p-5">
            <div className="flex items-end justify-between">
              <div>
                <p className="tabular text-4xl font-extrabold text-white">
                  {forecastShare}%
                </p>
                <p className="mt-1 text-[10px] font-bold text-[var(--muted)] uppercase">
                  Live forecasts
                </p>
              </div>
              <p className="text-right text-xs text-[var(--muted)]">
                {overview.forecast_projects} forecasts
                <br />
                {overview.optimization_projects} strategy sets
              </p>
            </div>
            <div className="mt-5 flex h-2 bg-[var(--surface-soft)]">
              <span
                className="h-full bg-[var(--signal)]"
                style={{ width: `${forecastShare}%` }}
              />
              <span className="h-full flex-1 bg-[var(--info)]" />
            </div>
            <div className="mt-3 flex justify-between text-[10px] text-[var(--muted)]">
              <span>Forecast</span>
              <span>Optimization</span>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

function AdminMetric({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="border-b border-[var(--line)] py-5 last:border-b-0 sm:border-r sm:px-5 sm:even:border-r-0 xl:border-b-0 xl:last:border-r-0 xl:even:border-r">
      <div className="flex items-center gap-2 text-[var(--muted)]">
        {icon}
        <p className="text-[10px] font-bold uppercase">{label}</p>
      </div>
      <p className="tabular mt-2 text-3xl font-extrabold text-white">{value}</p>
    </div>
  );
}

function AdminState({
  icon,
  title,
  detail,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  detail?: string;
  action?: string;
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
        {action && (
          <Link
            href={action}
            className="mt-5 inline-flex h-10 items-center gap-2 bg-[var(--signal)] px-4 text-xs font-extrabold text-black"
          >
            Continue
            <ArrowRight size={15} />
          </Link>
        )}
      </div>
    </div>
  );
}
