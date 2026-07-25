"""Freeze the 2025 research holdout as transparent evaluation forecasts.

These records are retrospective model-evaluation artifacts, not claims that a
public pre-release forecast existed. The generated payload is small enough to
bootstrap local and hosted read-only environments without shipping the source
research CSVs or embeddings.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error
from train_model_tournament import budget_segment, original_matrix

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "services" / "inference" / "artifacts"
OUTPUT = ROOT / "services" / "inference" / "data" / "holdout_2025_evaluation.json"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def factors(row: pd.Series) -> list[dict[str, object]]:
    known = {
        "synopsis_embedding": (
            "768-dimensional mean-pooled BERT vector",
            "Story",
            "Modeled directly by bert-xgb-v1.",
        ),
        "budget": (
            f"${float(row['budget']):,.0f} reported in the research corpus",
            "Package",
            "Log production budget is an original structured feature.",
        ),
        "genre": (
            str(row["genres_raw"]),
            "Story",
            "Primary genre is one-hot encoded in the original model.",
        ),
        "director_history": (
            str(row["director_name"]),
            "People",
            "Three director track-record features use the pre-2024 training set.",
        ),
        "release_month": (
            str(row["release_date"]),
            "Release",
            "Release timing is displayed but only decade is encoded by this baseline.",
        ),
    }
    definitions = [
        ("synopsis_embedding", "Synopsis embedding", "Story"),
        ("budget", "Production budget", "Package"),
        ("genre", "Genre-market history", "Story"),
        ("franchise_ip", "Franchise / IP", "Market"),
        ("director_history", "Director history", "People"),
        ("cast_history", "Cast history", "People"),
        ("studio_history", "Studio history", "People"),
        ("producer_writer_history", "Producer / writer history", "People"),
        ("release_month", "Release month", "Release"),
        ("holiday_window", "Holiday window", "Release"),
        ("nearby_competition", "Nearby competition", "Release"),
        ("runtime", "Runtime", "Package"),
        ("certification", "Certification", "Package"),
        ("distribution_scale", "Distribution scale", "Distribution"),
        ("premium_formats", "Premium formats", "Distribution"),
        ("origin_language", "Origin / language", "Market"),
        ("google_momentum", "Google search momentum", "Demand"),
        ("wikipedia_attention", "Wikipedia attention", "Demand"),
        ("trailer_momentum", "Trailer momentum", "Demand"),
        ("news_reddit_attention", "News / Reddit attention", "Demand"),
    ]
    output = []
    for key, label, group in definitions:
        if key in known:
            value, known_group, evidence = known[key]
            output.append(
                {
                    "key": key,
                    "label": label,
                    "group": known_group,
                    "value": value,
                    "impact": None,
                    "direction": "neutral",
                    "evidence": evidence,
                    "source_count": 1,
                }
            )
        else:
            output.append(
                {
                    "key": key,
                    "label": label,
                    "group": group,
                    "value": "Unavailable in the original research split",
                    "impact": None,
                    "direction": "unknown",
                    "evidence": "Not scored by bert-xgb-v1.",
                    "source_count": 0,
                }
            )
    return output


def main() -> None:
    train_path = DATA / "train.csv"
    holdout_source_path = DATA / "master_1970_2025_clean.csv"
    embeddings_path = DATA / "test_bert_embeddings.npy"
    model_path = ARTIFACTS / "bert-xgb-v1.ubj"
    manifest_path = ARTIFACTS / "bert-xgb-v1.json"

    train = pd.read_csv(train_path)
    holdout = pd.read_csv(holdout_source_path).query("year == 2025").reset_index(drop=True)
    embeddings = np.load(embeddings_path)
    if len(holdout) != len(embeddings):
        raise ValueError("The closed 2025 holdout and BERT embedding rows are not aligned")

    matrix = original_matrix(holdout, embeddings, train)
    model = xgb.XGBRegressor()
    model.load_model(model_path)
    log_predictions = model.predict(matrix)
    predictions = np.maximum(0.0, np.expm1(log_predictions))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    radii = manifest["conformal_log_radius"]

    rows = []
    covered = []
    for index, row in holdout.iterrows():
        radius = float(
            radii.get(
                budget_segment(float(row["budget"])),
                radii["global"],
            )
        )
        p10 = max(0.0, float(np.expm1(log_predictions[index] - radius)))
        p50 = float(predictions[index])
        p90 = max(p50, float(np.expm1(log_predictions[index] + radius)))
        actual = float(row["revenue"])
        covered.append(p10 <= actual <= p90)
        rows.append(
            {
                "title": str(row["title"]),
                "release_year": int(row["year"]),
                "release_date": str(row["release_date"]),
                "actual_worldwide_usd": actual,
                "targets": {
                    "worldwide_total": {
                        "p10": round(p10, 2),
                        "p50": round(p50, 2),
                        "p90": round(p90, 2),
                        "currency": "USD",
                    },
                    "domestic_total": None,
                    "domestic_opening": None,
                    "international_total": None,
                },
                "feature_vector_sha256": hashlib.sha256(
                    matrix[index].astype(np.float32).tobytes()
                ).hexdigest(),
                "factors": factors(row),
            }
        )

    generated_at = datetime.now(UTC)
    payload = {
        "schema_version": 1,
        "evaluation_kind": "retrospective_closed_holdout",
        "forecast_type": "evaluation",
        "model_version": "bert-xgb-v1",
        "generated_at": generated_at.isoformat(),
        "data_cutoff": generated_at.isoformat(),
        "is_ex_ante": False,
        "methodology_note": (
            "The model was trained through 2023 and these 2025 rows were held out, "
            "but the records were sealed retrospectively. They are model evaluation "
            "results, not reconstructed claims of publication before release."
        ),
        "source_checksums": {
            "holdout_csv": checksum(holdout_source_path),
            "holdout_embeddings": checksum(embeddings_path),
            "model_artifact": checksum(model_path),
        },
        "metrics": {
            "films": len(rows),
            "mae_usd": round(
                float(
                    mean_absolute_error(
                        holdout["revenue"].astype(float).to_numpy(),
                        predictions,
                    )
                ),
                2,
            ),
            "log_mae": round(
                float(
                    np.mean(
                        np.abs(
                            np.log1p(holdout["revenue"].astype(float).to_numpy()) - log_predictions
                        )
                    )
                ),
                6,
            ),
            "interval_coverage": round(float(np.mean(covered)), 6),
        },
        "rows": rows,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload["metrics"], indent=2, sort_keys=True))
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
