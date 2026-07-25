# SlateSignal Inference and Data Service

FastAPI API plus scheduled ingestion and forecast-ledger jobs.

## Development

```bash
python3.13 -m venv .venv
.venv/bin/pip install -e ".[dev,runtime]"
.venv/bin/alembic upgrade head
.venv/bin/uvicorn slatesignal.main:app --reload --port 8000
```

SQLite is the zero-setup default. Production uses a
`postgresql+psycopg://...` Neon URL and `AUTO_CREATE_SCHEMA=false`.

## CLI

```bash
.venv/bin/python -m slatesignal.cli seed
.venv/bin/python -m slatesignal.cli catalog-sync
.venv/bin/python -m slatesignal.cli imdb-sync
.venv/bin/python -m slatesignal.cli actuals-sync
.venv/bin/python -m slatesignal.cli buzz-sync
.venv/bin/python -m slatesignal.cli forecast-snapshot
.venv/bin/python -m slatesignal.cli verify-ledger
```

All jobs write `job_runs` status and stats. Catalog and source jobs are
idempotent by provider payload checksum. Forecast runs are unique by movie,
model, cutoff, horizon, and forecast type.

## Public API

- `GET /v1/movies`
- `GET /v1/movies/{id-or-slug}`
- `GET /v1/movies/{id-or-slug}/forecast`
- `GET /v1/movies/{id-or-slug}/forecast-history`
- `GET /v1/movies/{id-or-slug}/buzz`
- `GET /v1/backtests`
- `POST /v1/scenarios/forecast`
- `POST /v1/scenarios/optimize`

OpenAPI is available at `/docs`.

## Model Bundle

Small XGBoost artifacts and manifests are versioned in Git. The FP16 BERT ONNX
file is excluded and must exist at `BERT_ONNX_PATH` for new snapshot inference.
Cloud Run mounts it read-only from GCS. Public reads and portable launch
forecasts do not require the ONNX file.
