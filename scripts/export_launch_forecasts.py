"""Export sealed launch forecasts into a database-independent bootstrap file."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from slatesignal.core.database import SessionLocal
from slatesignal.domain.models import ForecastRun

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "services" / "inference" / "data" / "launch_forecasts.json"


def parsed(value: str) -> object:
    return json.loads(value)


def main() -> None:
    with SessionLocal() as db:
        candidates = list(
            db.scalars(
                select(ForecastRun)
                .where(ForecastRun.forecast_type == "official")
                .order_by(ForecastRun.data_cutoff, ForecastRun.movie_id)
            )
        )
        latest_by_movie = {forecast.movie_id: forecast for forecast in candidates}
        forecasts = sorted(
            latest_by_movie.values(),
            key=lambda item: (item.data_cutoff, item.movie.slug),
        )
        rows = [
            {
                "movie": {
                    "slug": forecast.movie.slug,
                    "title": forecast.movie.title,
                    "release_year": forecast.movie.release_year,
                },
                "model_version": forecast.model_version.version,
                "data_cutoff": forecast.data_cutoff.isoformat(),
                "horizon_days": forecast.horizon_days,
                "forecast_type": forecast.forecast_type,
                "targets": parsed(forecast.targets_json),
                "factors": parsed(forecast.factors_json),
                "buzz": parsed(forecast.buzz_json),
                "comparables": parsed(forecast.comparables_json),
                "fairness": parsed(forecast.fairness_json),
                "confidence_score": forecast.confidence_score,
                "feature_manifest_hash": forecast.feature_manifest_hash,
                "limitations": parsed(forecast.limitations_json),
                "generated_at": forecast.generated_at.isoformat(),
            }
            for forecast in forecasts
        ]
    payload = {
        "schema_version": 1,
        "purpose": "portable_precomputed_launch_forecasts",
        "rows": rows,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} forecasts to {OUTPUT}")


if __name__ == "__main__":
    main()
