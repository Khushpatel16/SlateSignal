"""Build sealed 2021-2024 temporal-fold evaluation forecasts.

These are retrospective walk-forward evaluations, not claims of publication
before release. Each fold trains only on earlier release years, chooses its
tree count and conformal radius on the immediately preceding year, and then
predicts the target year.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from train_model_tournament import genre_list

from slatesignal.modeling.features import (
    DirectorHistory,
    full_feature_vector,
    structured_vector,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "services" / "inference" / "artifacts"
OUTPUT = ROOT / "services" / "inference" / "data" / "historical_evaluations.json"
TARGET_YEARS = (2021, 2022, 2023, 2024)
MODEL_PARAMETERS = {
    "objective": "reg:squarederror",
    "learning_rate": 0.04,
    "max_depth": 4,
    "min_child_weight": 8,
    "subsample": 0.85,
    "colsample_bytree": 0.8,
    "reg_lambda": 2.0,
    "random_state": 42,
    "tree_method": "hist",
    "n_jobs": -1,
}


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def temporal_matrix(
    frame: pd.DataFrame,
    embeddings: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Create 15+768 vectors with director history frozen before each year."""

    if len(frame) != len(embeddings):
        raise ValueError("Frame and BERT embeddings are not aligned")
    histories: dict[str, list[float]] = defaultdict(list)
    prior_revenues: list[float] = []
    vectors: dict[int, np.ndarray] = {}

    for year in sorted(frame["year"].astype(int).unique()):
        year_rows = frame[frame["year"].astype(int) == year]
        fallback = float(np.median(prior_revenues)) if prior_revenues else 0.0
        pending: list[tuple[str, float]] = []
        for index, row in year_rows.iterrows():
            director = str(row["director_name"]) if pd.notna(row["director_name"]) else ""
            history_values = histories.get(director, [])
            history = (
                DirectorHistory(
                    films=len(history_values),
                    average_revenue=float(mean(history_values)),
                    maximum_revenue=float(max(history_values)),
                )
                if history_values
                else None
            )
            budget = float(row["budget"]) if pd.notna(row["budget"]) else 0.0
            structured = structured_vector(
                budget=budget,
                release_year=year,
                director_history=history,
                genres=genre_list(row["genres_raw"]),
            )
            if history is None:
                structured[2] = np.log1p(fallback)
            vectors[index] = full_feature_vector(structured, embeddings[index])[0]
            pending.append((director, float(row["revenue"])))
        for director, revenue in pending:
            if director:
                histories[director].append(revenue)
            prior_revenues.append(revenue)

    matrix = np.stack([vectors[index] for index in frame.index])
    target = np.log1p(frame["revenue"].astype(float).to_numpy())
    return matrix, np.asarray(target, dtype=np.float32)


def conformal_radius(residuals: np.ndarray) -> float:
    count = len(residuals)
    quantile = min(1.0, math.ceil((count + 1) * 0.8) / count)
    return float(np.quantile(residuals, quantile, method="higher"))


def factor_manifest(row: pd.Series) -> list[dict[str, object]]:
    available = {
        "synopsis_embedding": (
            "768-dimensional mean-pooled BERT vector",
            "Encoded from the research synopsis snapshot.",
        ),
        "budget": (
            (
                f"${float(row['budget']):,.0f} research-corpus estimate"
                if pd.notna(row["budget"])
                else "unavailable"
            ),
            "Log production budget is part of the temporal-fold model.",
        ),
        "genre": (
            ", ".join(genre_list(row["genres_raw"])),
            "Primary genre is one-hot encoded.",
        ),
        "director_history": (
            (str(row["director_name"]) if pd.notna(row["director_name"]) else "unavailable"),
            "Track record includes only films from earlier release years.",
        ),
        "release_month": (
            str(row["release_date"]),
            "Displayed as evidence; only release decade is encoded.",
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
        if key in available:
            value, evidence = available[key]
            output.append(
                {
                    "key": key,
                    "label": label,
                    "group": group,
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
                    "value": "unavailable in this temporal fold",
                    "impact": None,
                    "direction": "unknown",
                    "evidence": "Not scored by the 15-feature research architecture.",
                    "source_count": 0,
                }
            )
    return output


def train_fold(
    frame: pd.DataFrame,
    matrix: np.ndarray,
    target: np.ndarray,
    target_year: int,
) -> tuple[xgb.XGBRegressor, float, int]:
    calibration_year = target_year - 1
    tune_train = frame["year"].astype(int).to_numpy() < calibration_year
    calibration = frame["year"].astype(int).to_numpy() == calibration_year
    final_train = frame["year"].astype(int).to_numpy() < target_year
    if not tune_train.any() or not calibration.any():
        raise ValueError(f"Fold {target_year} has no temporal calibration split")

    tuning_model = xgb.XGBRegressor(
        **MODEL_PARAMETERS,
        n_estimators=800,
        early_stopping_rounds=35,
    )
    tuning_model.fit(
        matrix[tune_train],
        target[tune_train],
        eval_set=[(matrix[calibration], target[calibration])],
        verbose=False,
    )
    rounds = int(tuning_model.best_iteration) + 1
    calibration_prediction = tuning_model.predict(matrix[calibration])
    radius = conformal_radius(np.abs(target[calibration] - calibration_prediction))

    final_model = xgb.XGBRegressor(
        **MODEL_PARAMETERS,
        n_estimators=rounds,
    )
    final_model.fit(matrix[final_train], target[final_train], verbose=False)
    return final_model, radius, rounds


def main() -> None:
    train_path = DATA / "train.csv"
    train_embeddings_path = DATA / "train_bert_embeddings.npy"
    validation_path = DATA / "val.csv"
    validation_embeddings_path = DATA / "val_bert_embeddings.npy"
    train = pd.read_csv(train_path).reset_index(drop=True)
    validation = pd.read_csv(validation_path).reset_index(drop=True)
    frame = pd.concat([train, validation], ignore_index=True)
    embeddings = np.concatenate(
        [
            np.load(train_embeddings_path),
            np.load(validation_embeddings_path),
        ],
        axis=0,
    )
    matrix, target = temporal_matrix(frame, embeddings)
    years = frame["year"].astype(int).to_numpy()
    generated_at = datetime.now(UTC)
    model_versions = []
    rows = []
    fold_metrics: dict[str, dict[str, float | int]] = {}

    for target_year in TARGET_YEARS:
        model, radius, rounds = train_fold(
            frame,
            matrix,
            target,
            target_year,
        )
        target_mask = years == target_year
        target_indices = np.flatnonzero(target_mask)
        log_predictions = model.predict(matrix[target_mask])
        predictions = np.maximum(0.0, np.expm1(log_predictions))
        actuals = frame.loc[target_mask, "revenue"].astype(float).to_numpy()
        lower = np.maximum(0.0, np.expm1(log_predictions - radius))
        upper = np.maximum(predictions, np.expm1(log_predictions + radius))
        coverage = float(np.mean((actuals >= lower) & (actuals <= upper)))
        version = f"bert-xgb-temporal-{target_year}"
        artifact_path = ARTIFACTS / f"{version}.ubj"
        model.save_model(artifact_path)
        artifact_checksum = checksum(artifact_path)
        metrics = {
            "rows": int(target_mask.sum()),
            "mae_usd": round(
                float(mean_absolute_error(actuals, predictions)),
                2,
            ),
            "log_mae": round(
                float(np.mean(np.abs(np.log1p(actuals) - np.log1p(predictions)))),
                6,
            ),
            "r2": round(float(r2_score(actuals, predictions)), 6),
            "interval_coverage": round(coverage, 6),
            "conformal_log_radius": round(radius, 8),
            "rounds": rounds,
        }
        fold_metrics[str(target_year)] = metrics
        model_versions.append(
            {
                "version": version,
                "display_name": (f"Temporal BERT + XGBoost evaluation fold ({target_year})"),
                "model_kind": "bert_mean_pool_xgboost_temporal_fold",
                "artifact_uri": str(artifact_path.relative_to(ROOT)),
                "artifact_checksum": artifact_checksum,
                "training_cutoff": f"{target_year - 1}-12-31",
                "feature_manifest": {
                    "encoder": {
                        "name": "bert-base-uncased",
                        "hidden_size": 768,
                        "max_length": 512,
                        "pooling": "attention-mask-aware mean pooling",
                    },
                    "structured_features": 15,
                    "feature_count": 783,
                    "director_history": "strictly earlier release years",
                },
                "metrics": metrics,
            }
        )

        for local_index, frame_index in enumerate(target_indices):
            row = frame.iloc[frame_index]
            rows.append(
                {
                    "title": str(row["title"]),
                    "release_year": target_year,
                    "data_cutoff": f"{target_year}-01-01T00:00:00+00:00",
                    "model_version": version,
                    "targets": {
                        "worldwide_total": {
                            "p10": round(float(lower[local_index]), 2),
                            "p50": round(float(predictions[local_index]), 2),
                            "p90": round(float(upper[local_index]), 2),
                            "currency": "USD",
                        },
                        "domestic_total": None,
                        "domestic_opening": None,
                        "international_total": None,
                    },
                    "feature_vector_sha256": hashlib.sha256(
                        matrix[frame_index].astype(np.float32).tobytes()
                    ).hexdigest(),
                    "factors": factor_manifest(row),
                }
            )

    payload = {
        "schema_version": 1,
        "evaluation_kind": "retrospective_temporal_fold",
        "forecast_type": "evaluation",
        "generated_at": generated_at.isoformat(),
        "is_ex_ante": False,
        "methodology_note": (
            "Each target year was predicted by a model trained only on earlier "
            "release years, with tree count and interval radius selected on the "
            "immediately preceding year. The runs were sealed retrospectively and "
            "must not be described as forecasts published before release."
        ),
        "limitations": [
            "Research metadata was assembled after release; temporal target separation "
            "does not prove every metadata field was public at the simulated cutoff.",
            "The popularity-selected research corpus is not a theatrical census.",
            "Revenue is nominal USD and only worldwide total is modeled.",
            "No post-release ratings, social metrics, or protected attributes are inputs.",
        ],
        "source_checksums": {
            "train_csv": checksum(train_path),
            "train_embeddings": checksum(train_embeddings_path),
            "validation_csv": checksum(validation_path),
            "validation_embeddings": checksum(validation_embeddings_path),
        },
        "metrics": fold_metrics,
        "model_versions": model_versions,
        "rows": rows,
    }
    OUTPUT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(fold_metrics, indent=2, sort_keys=True))
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
