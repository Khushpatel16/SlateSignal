"""Calibrate and freeze the deployable bert-xgb-v1 research baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ARTIFACTS = ROOT / "services" / "inference" / "artifacts"
MODEL_PATH = ARTIFACTS / "bert-xgb-v1.ubj"
MANIFEST_PATH = ARTIFACTS / "bert-xgb-v1.json"
HISTORY_PATH = ARTIFACTS / "director-history-v1.json"
GOLDEN_PATH = ARTIFACTS / "golden-val-v1.json"
RUNTIME_GOLDEN_PATH = ARTIFACTS / "golden-runtime-v1.json"

GENRES = [
    "Action",
    "Animation",
    "Comedy",
    "Drama",
    "Fantasy",
    "Horror",
    "Other",
    "Romance",
    "SciFi",
    "Thriller",
]
STRUCTURED = [
    "log_budget",
    "decade",
    "director_avg_revenue_log",
    "director_num_films",
    "director_max_revenue_log",
    *(f"genre_{genre}" for genre in GENRES),
]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def primary_genre(raw: object) -> str:
    value = str(raw).casefold()
    checks = [
        ("action", "Action"),
        ("comedy", "Comedy"),
        ("drama", "Drama"),
        ("thriller", "Thriller"),
        ("horror", "Horror"),
        ("romance", "Romance"),
        ("sci-fi", "SciFi"),
        ("science fiction", "SciFi"),
        ("fantasy", "Fantasy"),
        ("animation", "Animation"),
    ]
    return next((genre for key, genre in checks if key in value), "Other")


def director_history(train: pd.DataFrame) -> dict[str, dict[str, float | int]]:
    output: dict[str, dict[str, float | int]] = {}
    for director, rows in train.groupby("director_name", dropna=True):
        revenues = rows["revenue"].astype(float).to_numpy()
        output[str(director)] = {
            "films": len(revenues),
            "avg_revenue": round(float(revenues.mean()), 6),
            "max_revenue": round(float(revenues.max()), 6),
            "latest_year": int(rows["year"].max()),
        }
    return output


def feature_matrix(
    frame: pd.DataFrame,
    embeddings: np.ndarray,
    histories: dict[str, dict[str, float | int]],
    fallback_revenue: float,
) -> np.ndarray:
    rows: list[list[float]] = []
    for row in frame.itertuples(index=False):
        history = histories.get(str(row.director_name))
        average = float(history["avg_revenue"]) if history else fallback_revenue
        maximum = float(history["max_revenue"]) if history else 0.0
        films = float(history["films"]) if history else 0.0
        genre = primary_genre(row.genres_raw)
        rows.append(
            [
                float(np.log1p(float(row.budget))),
                float(row.decade),
                float(np.log1p(average)),
                films,
                float(np.log1p(maximum)),
                *(1.0 if candidate == genre else 0.0 for candidate in GENRES),
            ]
        )
    structured = np.asarray(rows, dtype=np.float32)
    if structured.shape[1] != 15 or embeddings.shape[1] != 768:
        raise ValueError("Unexpected baseline feature shape")
    if len(structured) != len(embeddings):
        raise ValueError("Validation rows and embeddings are not aligned")
    return np.concatenate([structured, embeddings.astype(np.float32)], axis=1)


def budget_segment(value: float) -> str:
    if value < 5_000_000:
        return "micro"
    if value < 20_000_000:
        return "low"
    if value < 80_000_000:
        return "mid"
    if value < 180_000_000:
        return "high"
    return "blockbuster"


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(DATA / "train.csv")
    validation = pd.read_csv(DATA / "val.csv")
    embeddings = np.load(DATA / "val_bert_embeddings.npy")
    histories = director_history(train)
    fallback_revenue = float(train["revenue"].median())
    matrix = feature_matrix(
        validation,
        embeddings,
        histories,
        fallback_revenue,
    )

    model = xgb.XGBRegressor()
    model.load_model(MODEL_PATH)
    log_predictions = model.predict(matrix)
    predictions = np.expm1(log_predictions)
    actuals = validation["revenue"].astype(float).to_numpy()
    log_actuals = np.log1p(actuals)
    residuals = np.abs(log_actuals - log_predictions)
    global_radius = float(np.quantile(residuals, 0.8, method="higher"))
    radii = {"global": global_radius}
    segments = validation["budget"].astype(float).map(budget_segment)
    for segment in ("micro", "low", "mid", "high", "blockbuster"):
        values = residuals[segments.to_numpy() == segment]
        radii[segment] = (
            float(np.quantile(values, 0.8, method="higher")) if len(values) >= 15 else global_radius
        )

    lower = np.expm1(log_predictions - np.asarray([radii[item] for item in segments]))
    upper = np.expm1(log_predictions + np.asarray([radii[item] for item in segments]))
    coverage = float(np.mean((actuals >= np.maximum(0, lower)) & (actuals <= upper)))
    model_checksum = checksum(MODEL_PATH)
    metrics = {
        "validation_period": "2024",
        "rows": len(validation),
        "mae_usd": round(float(mean_absolute_error(actuals, predictions)), 2),
        "log_mae": round(float(np.mean(residuals)), 6),
        "r2": round(float(r2_score(actuals, predictions)), 6),
        "interval_nominal_coverage": 0.8,
        "interval_empirical_coverage": round(coverage, 6),
    }
    manifest = {
        "schema_version": 1,
        "version": "bert-xgb-v1",
        "display_name": "Original BERT + XGBoost research baseline",
        "model_kind": "bert_mean_pool_xgboost",
        "target": "log1p_worldwide_gross_usd",
        "training_cutoff": "2023-12-31",
        "encoder": {
            "name": "bert-base-uncased",
            "hidden_size": 768,
            "max_length": 512,
            "pooling": "attention-mask-aware mean pooling",
        },
        "structured_features": STRUCTURED,
        "director_history_fallback_revenue": fallback_revenue,
        "feature_count": 783,
        "model_sha256": model_checksum,
        "source_checksums": {
            "train_csv": checksum(DATA / "train.csv"),
            "train_embeddings": checksum(DATA / "train_bert_embeddings.npy"),
            "validation_csv": checksum(DATA / "val.csv"),
            "validation_embeddings": checksum(DATA / "val_bert_embeddings.npy"),
        },
        "conformal_log_radius": {key: round(value, 8) for key, value in radii.items()},
        "metrics": metrics,
        "research_reported_metrics": {
            "structured_baseline_mae_usd": 141_210_000,
            "tfidf_xgboost_mae_usd": 128_990_000,
            "bert_xgboost_mae_usd": 115_030_000,
            "bert_xgboost_r2": 0.382,
        },
        "limitations": [
            "Original training rows were selected by post-release popularity and are not a census.",
            "Nominal historical dollars were not inflation-normalized in this baseline.",
            "Training-time structured rows and embeddings require a corrected successor audit.",
            "Only worldwide gross is supported; secondary targets remain unavailable.",
            "Buzz is not an input to this baseline and no hand-authored social multiplier is used.",
        ],
    }
    HISTORY_PATH.write_text(
        json.dumps(histories, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    golden = {
        "model_sha256": model_checksum,
        "feature_matrix_sha256": hashlib.sha256(matrix.tobytes()).hexdigest(),
        "rows": [
            {
                "title": str(validation.iloc[index]["title"]),
                "year": int(validation.iloc[index]["year"]),
                "prediction_log": round(float(log_predictions[index]), 8),
                "prediction_usd": round(float(predictions[index]), 2),
                "feature_sha256": hashlib.sha256(matrix[index].tobytes()).hexdigest(),
            }
            for index in range(min(12, len(validation)))
        ],
    }
    GOLDEN_PATH.write_text(
        json.dumps(golden, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    first = validation.iloc[0]
    first_history = histories.get(str(first["director_name"]))
    runtime_golden = {
        "schema_version": 1,
        "model_sha256": model_checksum,
        "title": str(first["title"]),
        "input": {
            "budget": float(first["budget"]),
            "release_year": int(first["year"]),
            "genres": [primary_genre(first["genres_raw"])],
            "director_history": first_history,
        },
        "embedding": [float(value) for value in embeddings[0].astype(np.float32)],
        "expected": {
            "structured": [float(value) for value in matrix[0, :15]],
            "feature_sha256": hashlib.sha256(matrix[0].tobytes()).hexdigest(),
            "prediction_log": float(log_predictions[0]),
            "prediction_usd": float(predictions[0]),
        },
    }
    RUNTIME_GOLDEN_PATH.write_text(
        json.dumps(
            runtime_golden,
            indent=2,
            ensure_ascii=True,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(metrics, indent=2))
    print(f"Conformal radii: {radii}")


if __name__ == "__main__":
    main()
