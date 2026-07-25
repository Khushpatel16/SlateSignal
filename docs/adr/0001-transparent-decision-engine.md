# ADR 0001: Real-Film Forecast Ledger as the Primary Product

**Status:** Accepted  
**Date:** 2026-07-24

## Context

The original project was a 6,437-film BERT + XGBoost research study. An interim
product prototype shifted the main experience toward fictional concept
packages and a deterministic heuristic engine. That did not match the research
goal and made it impossible to prove how an unreleased real-film prediction
changed as release approached.

## Decision

Make real-film forecasting the primary product and retain concept optimization
only as a separately labeled lab.

Official forecasts are precomputed at T-180, T-90, T-30, and T-7, then sealed
in a SHA-256 hash chain with data cutoff, evidence timestamps, model version,
feature manifest, and intervals. Released-film actuals append to the record.

Preserve `bert-xgb-v1` exactly enough to replay golden outputs. Correct known
research defects in a candidate model, but promote only when temporal accuracy,
coverage, and fairness gates all pass.

## Consequences

Positive:

- the product answers the original research question
- forward forecasts become independently auditable
- missing data and unsupported targets remain visible
- recruiter-facing claims can be traced to code, artifacts, and tests
- normal page loads do not pay BERT inference latency

Negative:

- exhaustive catalog quality depends on source credentials and scheduled jobs
- the preserved baseline has high blockbuster error
- a useful ledger takes time to accumulate genuine ex-ante history
- model files and IMDb jobs need infrastructure beyond Vercel alone

## Rejected Alternatives

Serving fictional demo films was rejected because it confused scenario
simulation with official prediction. Applying hand-authored buzz multipliers
was rejected because it could not be temporally validated. Promoting the
corrected candidate on point-estimate improvement alone was rejected because
coverage and fairness gates did not pass.
