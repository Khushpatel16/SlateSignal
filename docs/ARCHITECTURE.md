# Architecture

## System Boundaries

### Web

`apps/web` is a Next.js App Router application. It owns presentation,
interaction state, accessibility, account workflows, and a same-origin proxy to
FastAPI. It contains no source credentials and performs no authoritative model
calculation.

### API

`services/inference` is a typed FastAPI service. SQLAlchemy owns persistence,
Alembic owns schema evolution, Pydantic owns public contracts, and Argon2-backed
opaque sessions protect saved work. Public forecast reads are precomputed and
do not run BERT on the request path.

### Scheduled Data Plane

The `slatesignal` CLI runs as Cloud Run Jobs:

| Job | Cadence | Responsibility |
| --- | --- | --- |
| `catalog-sync` | nightly | TMDB US theatrical discovery and enrichment |
| `buzz-sync` | daily | Wikimedia, GDELT, YouTube, and approved Reddit observations |
| `actuals-sync` | nightly | Wikidata and Wikipedia gross reconciliation |
| `imdb-sync` | weekly | IMDb canonical title, cast, and crew identity join |
| `forecast-snapshot` | daily | due T-180, T-90, T-30, and T-7 ledger locks |

Google Trends remains an adapter boundary until an approved API credential is
available. SlateSignal does not silently replace it with unofficial scraping.

## Persistent Domain

The database contains movies, external identifiers, people, credits, companies,
territorial releases, source observations, buzz snapshots, actual grosses,
model versions, forecast runs, ledger entries, watchlists, users, saved
projects, sessions, and job runs.

Source observations are append-only facts identified by movie, provider, type,
and payload checksum. Actual gross rows are provider-specific. The read model
selects the strongest current claim but marks differences over 3% as a
conflict and returns every competing value.

## Forecast Lifecycle

1. Catalog and buzz jobs append source observations.
2. A due snapshot loads only evidence where `observed_at <= data_cutoff`.
3. The encoder produces a 768-dimensional mean-pooled BERT vector.
4. The model returns P10/P50/P90 worldwide gross.
5. The run stores factor context, evidence hashes, limitations, and model version.
6. The ledger hashes the canonical payload and previous ledger hash.
7. Released-film actuals are appended without changing the sealed run.
8. Backtests score only sealed runs and display `official` and `evaluation` separately.
9. Temporal-fold artifacts carry `is_ex_ante: false`; simulated cutoffs never
   imply that a forecast was publicly issued on that date.

SQLite drops timezone metadata, so ledger canonicalization explicitly restores
UTC before hashing. This is covered by tamper-detection tests.

## Model Boundaries

`bert-xgb-v1` is the preserved research baseline. It supports worldwide total
only. Secondary targets are returned as unavailable rather than derived from
hand-authored ratios.

`multimodal-xgb-v2` is an unpromoted candidate. Promotion requires:

1. improved temporal log-MAE
2. dollar MAE no more than 5% worse
3. 75-85% empirical coverage for the nominal 80% interval
4. no material audited-group normalized-error regression

The concept lab is a separately labeled counterfactual tool. Its package and
profitability assumptions are not substituted into official movie forecasts.

## Deployment and Scaling

The API is stateless outside PostgreSQL. Model files are immutable GCS objects
mounted read-only. The public service can scale to zero because launch and due
forecasts are precomputed. Jobs receive larger CPU and memory allocations for
IMDb joins and BERT inference.

The production request path is:

```text
browser -> Vercel -> /api/v1 proxy -> Cloud Run -> Neon PostgreSQL
```

Session cookies remain HTTP-only, same-site, and secure. `WEB_ORIGIN` restricts
CORS to the final web origin. For multiple API replicas, replace the local
rate limiter with a shared gateway or Redis-backed limiter.

## Failure Behavior

- Missing API: the UI shows unavailable and never inserts demo films.
- Missing source field: uncertainty remains wide or the target is unavailable.
- Source disagreement: the actual is marked conflicted and alternatives remain visible.
- Missing ONNX mount: public precomputed reads continue; snapshot inference fails loudly.
- Ledger mutation: verification fails at the first altered sequence.
- Candidate promotion failure: the baseline remains active and the failed gate is public.
