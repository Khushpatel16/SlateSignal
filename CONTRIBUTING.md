# Contributing

SlateSignal treats a forecast as a decision aid, not a promise. Changes that
alter financial outputs must include tests, a model-card note, and a comparison
against representative budget segments.

## Local checks

```bash
make check
make build
```

Run browser journeys from `apps/web` with `npm run test:e2e`.

## Pull requests

Keep changes scoped. Document user-visible behavior, migrations, new
environment variables, privacy implications, and calibration impact. Do not
commit raw datasets, model binaries, secrets, runtime databases, or generated
test output.

## Data and fairness

Use only data with a documented license and provenance. Do not add protected
attributes as predictive features. Any group-level evaluation must report
sample sizes, error distributions, and known confounders.
