"""Train and evaluate the corrected SlateSignal multimodal candidate.

Model selection uses an internal 2022-2023 fold. The untouched 2024 split is
used for conformal calibration and temporal validation; the 24 closed 2025
films remain the final holdout.
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score

from slatesignal.modeling.features import (
    DirectorHistory,
    full_feature_vector,
    structured_vector,
)
from slatesignal.modeling.inflation import (
    annual_cpi,
    from_base_year_dollars,
    to_base_year_dollars,
)
from slatesignal.modeling.multimodal_features import (
    MULTIMODAL_FEATURE_NAMES,
    MULTIMODAL_STRUCTURED_FEATURES,
    MultimodalInput,
    TrackRecord,
    full_multimodal_vector,
    structured_multimodal_vector,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SERVICE_DATA = ROOT / "services" / "inference" / "data"
ARTIFACTS = ROOT / "services" / "inference" / "artifacts"
WEB_DATA = ROOT / "apps" / "web" / "src" / "lib"
CPI_PATH = SERVICE_DATA / "cpi_monthly_1970_2026.csv"


def parse_list(raw: object) -> list[str]:
    if not isinstance(raw, str) or not raw:
        return []
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def parse_runtime(raw: object) -> int | None:
    if not isinstance(raw, str):
        return None
    hours = re.search(r"(\d+)\s*h", raw)
    minutes = re.search(r"(\d+)\s*m", raw)
    value = (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)
    return value or None


def parse_release_date(raw: object) -> datetime | None:
    if not isinstance(raw, str):
        return None
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+\d{1,2},\s+\d{4}",
        raw,
    )
    if not match:
        return None
    return datetime.strptime(match.group(0), "%B %d, %Y").replace(tzinfo=UTC)


def genre_list(raw: object) -> list[str]:
    value = str(raw).casefold()
    output = []
    mapping = {
        "action": "Action",
        "animation": "Animation",
        "comedy": "Comedy",
        "drama": "Drama",
        "fantasy": "Fantasy",
        "horror": "Horror",
        "romance": "Romance",
        "sci-fi": "Science Fiction",
        "science fiction": "Science Fiction",
        "thriller": "Thriller",
    }
    for key, genre in mapping.items():
        if key in value and genre not in output:
            output.append(genre)
    return output or ["Other"]


def append_history(
    store: dict[str, list[float]],
    names: list[str],
    revenue: float,
) -> None:
    for name in dict.fromkeys(names):
        if name:
            store[name].append(revenue)


def aggregate_history(
    store: dict[str, list[float]],
    names: list[str],
) -> TrackRecord:
    values = [revenue for name in dict.fromkeys(names) for revenue in store.get(name, [])]
    if not values:
        return TrackRecord()
    return TrackRecord(
        films=len(values),
        average_revenue=float(mean(values)),
        maximum_revenue=float(max(values)),
        missing=False,
    )


def build_corrected_matrix(
    frame: pd.DataFrame,
    embeddings: np.ndarray,
    *,
    cpi: dict[int, float],
) -> tuple[np.ndarray, np.ndarray, dict[str, dict[str, dict[str, float | int]]]]:
    if len(frame) != len(embeddings):
        raise ValueError("Frame and BERT embeddings are not aligned")
    director_store: dict[str, list[float]] = defaultdict(list)
    cast_store: dict[str, list[float]] = defaultdict(list)
    studio_store: dict[str, list[float]] = defaultdict(list)
    vectors: dict[int, np.ndarray] = {}
    targets: dict[int, float] = {}

    for year in sorted(frame["year"].astype(int).unique()):
        year_rows = frame[frame["year"].astype(int) == year]
        pending: list[tuple[str, list[str], list[str], float]] = []
        for index, row in year_rows.iterrows():
            revenue_real = to_base_year_dollars(
                float(row["revenue"]),
                year=year,
                values=cpi,
            )
            budget = float(row["budget"]) if pd.notna(row["budget"]) else 0.0
            cast = parse_list(row["cast_raw"])[:5]
            studios = parse_list(row["production_company"])[:3]
            director = str(row["director_name"]) if pd.notna(row["director_name"]) else ""
            release = parse_release_date(row["release_date"])
            item = MultimodalInput(
                title=str(row["title"]),
                budget_real_2025=to_base_year_dollars(
                    budget,
                    year=year,
                    values=cpi,
                ),
                budget_missing=budget <= 0,
                release_year=year,
                release_date=release.date() if release else None,
                director=aggregate_history(director_store, [director]),
                cast=aggregate_history(cast_store, cast),
                studio=aggregate_history(studio_store, studios),
                genres=genre_list(row["genres_raw"]),
                runtime_minutes=parse_runtime(row["duration"]),
                certification=(str(row["MPA"]) if pd.notna(row["MPA"]) else None),
            )
            structured = structured_multimodal_vector(item)
            vectors[index] = full_multimodal_vector(structured, embeddings[index])
            targets[index] = math.log1p(revenue_real)
            pending.append((director, cast, studios, revenue_real))
        for director, cast, studios, revenue_real in pending:
            append_history(director_store, [director], revenue_real)
            append_history(cast_store, cast, revenue_real)
            append_history(studio_store, studios, revenue_real)

    history_payload = {
        "directors": summarize_store(director_store),
        "cast": summarize_store(cast_store),
        "studios": summarize_store(studio_store),
    }
    matrix = np.stack([vectors[index] for index in frame.index])
    target = np.asarray([targets[index] for index in frame.index], dtype=np.float32)
    return matrix, target, history_payload


def summarize_store(
    store: dict[str, list[float]],
) -> dict[str, dict[str, float | int]]:
    return {
        name: {
            "films": len(values),
            "avg_revenue": round(float(mean(values)), 6),
            "max_revenue": round(float(max(values)), 6),
        }
        for name, values in store.items()
        if name and values
    }


def original_matrix(
    frame: pd.DataFrame,
    embeddings: np.ndarray,
    train: pd.DataFrame,
) -> np.ndarray:
    histories: dict[str, list[float]] = defaultdict(list)
    for row in train.itertuples(index=False):
        if isinstance(row.director_name, str):
            histories[row.director_name].append(float(row.revenue))
    fallback = float(train["revenue"].median())
    vectors = []
    for index, row in frame.reset_index(drop=True).iterrows():
        values = histories.get(str(row["director_name"]), [])
        history = (
            None
            if not values
            else {
                "films": len(values),
                "average": mean(values),
                "maximum": max(values),
            }
        )
        structured = structured_vector(
            budget=float(row["budget"]),
            release_year=int(row["year"]),
            director_history=(
                None
                if history is None
                else DirectorHistory(
                    films=int(history["films"]),
                    average_revenue=float(history["average"]),
                    maximum_revenue=float(history["maximum"]),
                )
            ),
            genres=genre_list(row["genres_raw"]),
        )
        if history is None:
            structured[2] = np.log1p(fallback)
        vectors.append(full_feature_vector(structured, embeddings[index])[0])
    return np.stack(vectors)


def nominal_predictions(
    log_real_predictions: np.ndarray,
    years: np.ndarray,
    cpi: dict[int, float],
) -> np.ndarray:
    return np.asarray(
        [
            from_base_year_dollars(
                float(np.expm1(value)),
                year=int(year),
                values=cpi,
            )
            for value, year in zip(log_real_predictions, years, strict=True)
        ]
    )


def metrics(actual: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    return {
        "mae_usd": round(float(mean_absolute_error(actual, predicted)), 2),
        "log_mae": round(
            float(np.mean(np.abs(np.log1p(actual) - np.log1p(predicted)))),
            6,
        ),
        "r2": round(float(r2_score(actual, predicted)), 6),
    }


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
    cpi = annual_cpi(CPI_PATH)
    train = pd.read_csv(DATA / "train.csv").reset_index(drop=True)
    validation = pd.read_csv(DATA / "val.csv").reset_index(drop=True)
    holdout = (
        pd.read_csv(DATA / "master_1970_2025_clean.csv")
        .query("year == 2025")
        .reset_index(drop=True)
    )
    train_embeddings = np.load(DATA / "train_bert_embeddings.npy")
    validation_embeddings = np.load(DATA / "val_bert_embeddings.npy")
    holdout_embeddings = np.load(DATA / "test_bert_embeddings.npy")
    combined = pd.concat([train, validation, holdout], ignore_index=True)
    combined_embeddings = np.concatenate(
        [train_embeddings, validation_embeddings, holdout_embeddings],
        axis=0,
    )
    corrected_matrix, corrected_target, histories = build_corrected_matrix(
        combined,
        combined_embeddings,
        cpi=cpi,
    )
    train_count = len(train)
    validation_count = len(validation)
    x_train = corrected_matrix[:train_count]
    y_train = corrected_target[:train_count]
    x_validation = corrected_matrix[train_count : train_count + validation_count]
    y_validation = corrected_target[train_count : train_count + validation_count]
    x_holdout = corrected_matrix[train_count + validation_count :]

    internal_train = train["year"].astype(int).to_numpy() <= 2021
    internal_validation = train["year"].astype(int).to_numpy() >= 2022
    candidates = [
        {"max_depth": 4, "learning_rate": 0.025, "min_child_weight": 4},
        {"max_depth": 5, "learning_rate": 0.025, "min_child_weight": 6},
        {"max_depth": 4, "learning_rate": 0.04, "min_child_weight": 8},
        {"max_depth": 6, "learning_rate": 0.02, "min_child_weight": 8},
    ]
    tournament_rows = []
    best: tuple[float, dict[str, float | int], int] | None = None
    for params in candidates:
        model = xgb.XGBRegressor(
            n_estimators=1600,
            objective="reg:squarederror",
            subsample=0.82,
            colsample_bytree=0.78,
            reg_alpha=0.04,
            reg_lambda=1.4,
            random_state=42,
            n_jobs=1,
            early_stopping_rounds=80,
            **params,
        )
        model.fit(
            x_train[internal_train],
            y_train[internal_train],
            eval_set=[(x_train[internal_validation], y_train[internal_validation])],
            verbose=False,
        )
        prediction = model.predict(x_train[internal_validation])
        score = float(np.mean(np.abs(y_train[internal_validation] - prediction)))
        rounds = int(model.best_iteration + 1)
        row = {**params, "rounds": rounds, "internal_log_mae": round(score, 6)}
        tournament_rows.append(row)
        if best is None or score < best[0]:
            best = (score, params, rounds)
    if best is None:
        raise RuntimeError("No tournament candidate completed")

    _, best_params, best_rounds = best
    corrected = xgb.XGBRegressor(
        n_estimators=best_rounds,
        objective="reg:squarederror",
        subsample=0.82,
        colsample_bytree=0.78,
        reg_alpha=0.04,
        reg_lambda=1.4,
        random_state=42,
        n_jobs=1,
        **best_params,
    )
    corrected.fit(x_train, y_train, verbose=False)
    validation_log_prediction = corrected.predict(x_validation)
    holdout_log_prediction = corrected.predict(x_holdout)
    validation_prediction = nominal_predictions(
        validation_log_prediction,
        validation["year"].astype(int).to_numpy(),
        cpi,
    )
    holdout_prediction = nominal_predictions(
        holdout_log_prediction,
        holdout["year"].astype(int).to_numpy(),
        cpi,
    )

    original = xgb.XGBRegressor()
    original.load_model(ARTIFACTS / "bert-xgb-v1.ubj")
    original_validation = np.expm1(
        original.predict(original_matrix(validation, validation_embeddings, train))
    )
    original_holdout = np.expm1(
        original.predict(original_matrix(holdout, holdout_embeddings, train))
    )
    validation_actual = validation["revenue"].astype(float).to_numpy()
    holdout_actual = holdout["revenue"].astype(float).to_numpy()

    residuals = np.abs(y_validation - validation_log_prediction)
    segments = validation["budget"].astype(float).map(budget_segment).to_numpy()
    global_radius = float(np.quantile(residuals, 0.8, method="higher"))
    radii = {"global": global_radius}
    for segment in ("micro", "low", "mid", "high", "blockbuster"):
        values = residuals[segments == segment]
        radii[segment] = (
            float(np.quantile(values, 0.8, method="higher")) if len(values) >= 15 else global_radius
        )
    holdout_radii = np.asarray(
        [radii[budget_segment(value)] for value in holdout["budget"].astype(float)]
    )
    lower = nominal_predictions(
        holdout_log_prediction - holdout_radii,
        holdout["year"].astype(int).to_numpy(),
        cpi,
    )
    upper = nominal_predictions(
        holdout_log_prediction + holdout_radii,
        holdout["year"].astype(int).to_numpy(),
        cpi,
    )
    coverage = float(np.mean((holdout_actual >= lower) & (holdout_actual <= upper)))

    periods = {
        "2024_validation": {
            "original": metrics(validation_actual, original_validation),
            "corrected": metrics(validation_actual, validation_prediction),
        },
        "2025_closed_holdout": {
            "original": metrics(holdout_actual, original_holdout),
            "corrected": metrics(holdout_actual, holdout_prediction),
            "interval_coverage": round(coverage, 6),
            "films": len(holdout),
        },
    }
    technical_gates = {
        "improves_temporal_log_mae": all(
            values["corrected"]["log_mae"] < values["original"]["log_mae"]
            for values in periods.values()
        ),
        "dollar_mae_within_5_percent": all(
            values["corrected"]["mae_usd"] <= values["original"]["mae_usd"] * 1.05
            for values in periods.values()
        ),
        "coverage_between_75_and_85_percent": 0.75 <= coverage <= 0.85,
        "audited_group_error_not_worse": False,
    }
    promoted = all(technical_gates.values())

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    corrected_path = ARTIFACTS / "multimodal-xgb-v2.ubj"
    corrected.save_model(corrected_path)
    model_sha = hashlib.sha256(corrected_path.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "version": "multimodal-xgb-v2",
        "display_name": "Corrected time-frozen BERT + structured candidate",
        "model_kind": "bert_mean_pool_xgboost_corrected",
        "training_cutoff": "2023-12-31",
        "target": "log1p_worldwide_gross_real_2025_usd",
        "feature_count": len(MULTIMODAL_FEATURE_NAMES),
        "structured_features": list(MULTIMODAL_STRUCTURED_FEATURES),
        "encoder": {
            "name": "bert-base-uncased",
            "hidden_size": 768,
            "max_length": 512,
            "pooling": "attention-mask-aware mean pooling",
        },
        "best_parameters": {**best_params, "n_estimators": best_rounds},
        "conformal_log_radius": {key: round(value, 8) for key, value in radii.items()},
        "evaluation": periods,
        "promotion_gates": technical_gates,
        "promoted": promoted,
        "promotion_note": (
            "Promotion is blocked until a Wikidata-backed matched-cohort fairness audit "
            "has enough representation."
            if not technical_gates["audited_group_error_not_worse"]
            else "All promotion gates passed."
        ),
        "model_sha256": model_sha,
        "cpi_source": {
            "series": "CPIAUCSL",
            "provider": "Federal Reserve Bank of St. Louis / U.S. BLS",
            "projection_after_latest_observation": "2.4% annual, labeled assumption",
        },
        "limitations": [
            "The research corpus is popularity-selected rather than a theatrical census.",
            (
                "Historical premium-format, distribution-scale, and pre-release "
                "buzz fields are absent."
            ),
            "Secondary box-office targets await source-complete training labels.",
            "Franchise status uses a reproducible title-derived proxy in this candidate.",
        ],
    }
    (ARTIFACTS / "multimodal-xgb-v2.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    history_payload = {
        "schema_version": 1,
        "cutoff": "2025-12-31",
        "currency_basis": "real_2025_usd",
        **histories,
    }
    (ARTIFACTS / "multimodal-history-v2.json").write_text(
        json.dumps(history_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tournament = {
        "generated_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "films": 6437,
            "training": len(train),
            "validation_2024": len(validation),
            "holdout_2025": len(holdout),
        },
        "candidate_search": tournament_rows,
        "periods": periods,
        "conformal_holdout_coverage": round(coverage, 6),
        "promotion_gates": technical_gates,
        "promoted": promoted,
    }
    (ARTIFACTS / "model-tournament-v2.json").write_text(
        json.dumps(tournament, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    WEB_DATA.mkdir(parents=True, exist_ok=True)
    (WEB_DATA / "research-results.json").write_text(
        json.dumps(tournament, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(tournament, indent=2))


if __name__ == "__main__":
    main()
