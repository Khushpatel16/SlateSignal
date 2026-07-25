"use client";

import { useEffect, useRef, useState } from "react";
import { FlaskConical, Sparkles } from "lucide-react";

import { ConceptOptimizer } from "@/components/lab/concept-optimizer";
import { ForecastForm } from "@/components/lab/forecast-form";
import { ForecastResults } from "@/components/lab/forecast-results";
import { api } from "@/lib/api";
import { classNames } from "@/lib/format";
import {
  clearForecast,
  clearMovie,
  peekForecast,
  peekMovie,
} from "@/lib/project-transfer";
import {
  defaultScenarioRequest,
  scenarioFromMovie,
} from "@/lib/scenario-defaults";
import type { ForecastRequest, ForecastResponse } from "@/types/domain";

type Mode = "forecast" | "optimize";

export function GreenlightLab() {
  const [mode, setMode] = useState<Mode>("forecast");
  const [request, setRequest] = useState<ForecastRequest>(
    defaultScenarioRequest,
  );
  const [result, setResult] = useState<ForecastResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sequence = useRef(0);

  useEffect(() => {
    let active = true;
    const stagedForecast = peekForecast();
    if (stagedForecast) {
      queueMicrotask(() => {
        if (active) {
          setRequest(stagedForecast);
          clearForecast();
        }
      });
      return () => {
        active = false;
      };
    }

    const stagedMovie = peekMovie();
    if (stagedMovie) {
      const nextRequest = scenarioFromMovie(stagedMovie);
      queueMicrotask(() => {
        if (active) {
          setRequest(nextRequest);
          clearMovie();
        }
      });
      return () => {
        active = false;
      };
    }

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (mode !== "forecast") return;
    if (request.synopsis.trim().length < 40 || request.genres.length === 0) {
      return;
    }

    const current = ++sequence.current;
    const timer = window.setTimeout(() => {
      setPending(true);
      api
        .forecast(request)
        .then((response) => {
          if (sequence.current !== current) return;
          setResult(response);
          setError(null);
        })
        .catch(() => {
          if (sequence.current !== current) return;
          setError("The forecasting service is temporarily offline.");
        })
        .finally(() => {
          if (sequence.current === current) setPending(false);
        });
    }, 320);

    return () => window.clearTimeout(timer);
  }, [mode, request]);

  function usePlan(next: ForecastRequest) {
    setRequest(next);
    setMode("forecast");
  }

  const validationError =
    request.synopsis.trim().length < 40 || request.genres.length === 0
      ? "Add a synopsis of at least 40 characters and choose a genre."
      : null;

  return (
    <div>
      <header className="border-b border-[var(--line)] bg-[var(--canvas-raised)] px-5 py-4 sm:px-7">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-[var(--signal)]">
              <FlaskConical size={15} />
              <p className="text-[10px] font-bold uppercase">
                Counterfactual workspace
              </p>
            </div>
            <h1 className="mt-1 text-xl font-extrabold text-white">
              Greenlight Lab
            </h1>
          </div>

          <div
            aria-label="Lab mode"
            className="grid grid-cols-2 border border-[var(--line)]"
          >
            <button
              type="button"
              onClick={() => setMode("forecast")}
              className={classNames(
                "flex h-9 items-center gap-2 border-r border-[var(--line)] px-3 text-xs font-bold",
                mode === "forecast"
                  ? "bg-[var(--signal)] text-black"
                  : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
              )}
            >
              <FlaskConical size={14} />
              Live forecast
            </button>
            <button
              type="button"
              onClick={() => setMode("optimize")}
              className={classNames(
                "flex h-9 items-center gap-2 px-3 text-xs font-bold",
                mode === "optimize"
                  ? "bg-[var(--signal)] text-black"
                  : "text-[var(--muted)] hover:bg-[var(--surface)] hover:text-white",
              )}
            >
              <Sparkles size={14} />
              Optimize concept
            </button>
          </div>
        </div>
      </header>

      {mode === "forecast" ? (
        <div className="mx-auto grid max-w-[1600px] xl:grid-cols-[410px_minmax(0,1fr)]">
          <aside className="border-b border-[var(--line)] bg-[var(--canvas-raised)] xl:border-r xl:border-b-0">
            <ForecastForm value={request} onChange={setRequest} />
          </aside>
          <section className="min-w-0">
            <ForecastResults
              result={validationError ? null : result}
              pending={pending}
              error={validationError ?? error}
              request={request}
            />
          </section>
        </div>
      ) : (
        <ConceptOptimizer seed={request} onUsePlan={usePlan} />
      )}
    </div>
  );
}
