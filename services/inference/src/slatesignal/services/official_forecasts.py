from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.core.config import get_settings
from slatesignal.domain.models import (
    ForecastRun,
    ModelVersion,
    Movie,
)
from slatesignal.modeling.encoder import BertMeanPoolEncoder
from slatesignal.modeling.features import director_history_from_mapping
from slatesignal.modeling.predictor import BaselinePrediction, ResearchBaselinePredictor
from slatesignal.services.knowledge import get_knowledge_base
from slatesignal.services.ledger import seal_forecast
from slatesignal.services.movies import movie_buzz
from slatesignal.services.provenance import canonical_json, eligible_observations

PRODUCTION_FACTORS = (
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
)


@lru_cache
def get_research_predictor() -> ResearchBaselinePredictor:
    settings = get_settings()
    return ResearchBaselinePredictor(
        artifact_path=settings.model_artifact_path,
        manifest_path=settings.model_manifest_path,
        encoder=BertMeanPoolEncoder(
            model_name=settings.bert_model_name,
            onnx_path=settings.bert_onnx_path,
            tokenizer_path=settings.bert_tokenizer_path,
        ),
    )


@lru_cache
def _director_histories() -> dict[str, dict[str, object]]:
    path = Path(get_settings().director_history_path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def ensure_research_model_version(db: Session) -> ModelVersion:
    predictor = get_research_predictor()
    manifest = predictor.manifest
    version = str(manifest["version"])
    model_version = db.scalar(select(ModelVersion).where(ModelVersion.version == version))
    feature_manifest = canonical_json(
        {
            "encoder": manifest["encoder"],
            "structured_features": manifest["structured_features"],
            "feature_count": manifest["feature_count"],
            "director_history_fallback_revenue": manifest["director_history_fallback_revenue"],
        }
    )
    if model_version:
        model_version.artifact_uri = get_settings().model_artifact_path
        model_version.artifact_checksum = str(manifest["model_sha256"])
        model_version.feature_manifest_json = feature_manifest
        model_version.metrics_json = canonical_json(manifest["metrics"])
        return model_version
    model_version = ModelVersion(
        version=version,
        display_name=str(manifest["display_name"]),
        model_kind=str(manifest["model_kind"]),
        artifact_uri=get_settings().model_artifact_path,
        artifact_checksum=str(manifest["model_sha256"]),
        feature_manifest_json=feature_manifest,
        metrics_json=canonical_json(manifest["metrics"]),
        training_cutoff=datetime.fromisoformat(f"{manifest['training_cutoff']}T00:00:00").date(),
        promoted=False,
    )
    db.add(model_version)
    db.flush()
    return model_version


def create_locked_forecast(
    db: Session,
    *,
    movie: Movie,
    cutoff: datetime | None = None,
    forecast_type: str | None = None,
) -> ForecastRun:
    cutoff = cutoff or datetime.now(UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    horizon_days = (movie.release_date - cutoff.date()).days if movie.release_date else None
    model_version = ensure_research_model_version(db)
    kind = forecast_type or (
        "official"
        if movie.release_date is None or cutoff.date() < movie.release_date
        else "evaluation"
    )
    existing = db.scalar(
        select(ForecastRun).where(
            ForecastRun.movie_id == movie.id,
            ForecastRun.model_version_id == model_version.id,
            ForecastRun.data_cutoff == cutoff,
            ForecastRun.horizon_days == horizon_days,
            ForecastRun.forecast_type == kind,
        )
    )
    if existing:
        seal_forecast(db, existing)
        return existing

    budget, budget_status = _forecast_budget(db, movie, cutoff)
    histories = _director_histories()
    director = _director_name(movie)
    history = director_history_from_mapping(histories.get(director or ""))
    predictor = get_research_predictor()
    prediction = predictor.predict(
        text=movie.synopsis or movie.title,
        budget=budget,
        release_year=movie.release_year,
        director_history=history,
        genres=_json(movie.genres_json, []),
    )
    observations = eligible_observations(db, movie_id=movie.id, cutoff=cutoff)
    factors = _factor_manifest(
        db,
        movie=movie,
        prediction=prediction,
        budget=budget,
        budget_status=budget_status,
        cutoff=cutoff,
        director=director,
        director_films=history.films if history else 0,
    )
    buzz = [item.model_dump(mode="json") for item in movie_buzz(movie, cutoff=cutoff)]
    comparables = _comparables(db, movie, budget, cutoff)
    feature_manifest_hash = hashlib.sha256(model_version.feature_manifest_json.encode()).hexdigest()
    missing = [factor["label"] for factor in factors if factor["direction"] == "unknown"]
    limitations = list(predictor.manifest.get("limitations", []))
    limitations.extend(
        [
            "Secondary revenue targets are unavailable for this baseline.",
            (
                "Synopsis was unavailable; the title alone was encoded and uncertainty "
                "was retained."
                if not movie.synopsis
                else ""
            ),
            (
                f"Production budget was model-imputed at ${budget:,.0f} from pre-cutoff "
                "genre comparables."
                if budget_status == "model_imputed"
                else ""
            ),
            f"{len(missing)} of 20 production factors are not inputs to bert-xgb-v1.",
        ]
    )
    limitations = [item for item in limitations if item]
    interval_width = prediction.p90 - prediction.p10
    completeness = sum(item["direction"] != "unknown" for item in factors) / len(factors)
    confidence = max(
        0.1,
        min(
            0.86,
            0.35
            + completeness * 0.32
            + (0.10 if movie.synopsis else 0)
            + (0.09 if movie.budget else 0)
            - min(0.18, interval_width / max(1.0, prediction.p50) * 0.015),
        ),
    )
    forecast = ForecastRun(
        movie_id=movie.id,
        model_version_id=model_version.id,
        data_cutoff=cutoff,
        horizon_days=horizon_days,
        forecast_type=kind,
        targets_json=canonical_json(
            {
                "worldwide_total": {
                    "p10": round(prediction.p10, 2),
                    "p50": round(prediction.p50, 2),
                    "p90": round(prediction.p90, 2),
                    "currency": "USD",
                },
                "domestic_total": None,
                "domestic_opening": None,
                "international_total": None,
            }
        ),
        factors_json=canonical_json(factors),
        buzz_json=canonical_json(buzz),
        comparables_json=canonical_json(comparables),
        fairness_json=canonical_json(
            {
                "protected_attributes_used": False,
                "audit_status": "watch",
                "evaluation_only_attributes": ["gender annotations from Wikidata"],
                "cohort_definition": (
                    "Matched release year, genre, and budget cohorts with bootstrap "
                    "confidence intervals; evaluation only."
                ),
                "notes": [
                    "Protected attributes are excluded from model inputs.",
                    "Director history can carry opportunity-related proxy bias.",
                    "The original binary name-based gender analysis is not used here.",
                ],
            }
        ),
        evidence_manifest_json=canonical_json(
            [
                {
                    "id": item.id,
                    "source": item.source,
                    "observed_at": item.observed_at.isoformat(),
                    "raw_checksum": item.raw_checksum,
                }
                for item in observations
            ]
        ),
        confidence_score=confidence,
        feature_manifest_hash=feature_manifest_hash,
        limitations_json=canonical_json(limitations),
        generated_at=datetime.now(UTC),
    )
    db.add(forecast)
    db.flush()
    seal_forecast(db, forecast)
    db.commit()
    return forecast


def snapshot_eligible_movies(
    db: Session,
    *,
    force: bool = False,
    cutoff: datetime | None = None,
) -> dict[str, int]:
    cutoff = cutoff or datetime.now(UTC)
    movies = list(
        db.scalars(
            select(Movie).where(
                Movie.release_status.in_(
                    ["confirmed", "date_tentative", "year_only", "in_theaters"]
                )
            )
        )
    )
    stats = {"eligible": 0, "created": 0, "skipped": 0, "failed": 0}
    milestones = {180, 90, 30, 7}
    for movie in movies:
        horizon = (movie.release_date - cutoff.date()).days if movie.release_date else None
        due = force or (horizon is not None and horizon in milestones)
        if not due:
            stats["skipped"] += 1
            continue
        stats["eligible"] += 1
        try:
            create_locked_forecast(db, movie=movie, cutoff=cutoff)
            stats["created"] += 1
        except (FileNotFoundError, ImportError, OSError, ValueError):
            db.rollback()
            stats["failed"] += 1
    return stats


def _forecast_budget(
    db: Session,
    movie: Movie,
    cutoff: datetime,
) -> tuple[float, str]:
    if movie.budget and movie.budget > 0:
        return movie.budget, movie.budget_status
    genres = set(_json(movie.genres_json, []))
    candidates = list(
        db.scalars(
            select(Movie).where(
                Movie.release_year <= cutoff.year,
                Movie.release_status.in_(["released", "gross_closed"]),
                Movie.budget.is_not(None),
                Movie.budget > 0,
            )
        )
    )
    matching = [
        candidate.budget
        for candidate in candidates
        if genres.intersection(_json(candidate.genres_json, [])) and candidate.budget is not None
    ]
    if matching:
        return float(median(matching)), "model_imputed"
    return float(get_knowledge_base().global_stats["median_budget"]), "model_imputed"


def _director_name(movie: Movie) -> str | None:
    return next(
        (credit.person.name for credit in movie.credits if credit.job.casefold() == "director"),
        None,
    )


def _factor_manifest(
    db: Session,
    *,
    movie: Movie,
    prediction: BaselinePrediction,
    budget: float,
    budget_status: str,
    cutoff: datetime,
    director: str | None,
    director_films: int,
) -> list[dict[str, object]]:
    contributions = prediction.contributions
    genre_contribution = sum(
        value for key, value in contributions.items() if key.startswith("genre_")
    )
    director_contribution = sum(
        contributions.get(key, 0.0)
        for key in (
            "director_avg_revenue_log",
            "director_num_films",
            "director_max_revenue_log",
        )
    )
    competition = _competition_count(db, movie, cutoff)
    buzz_sources = {
        item.source for item in movie.buzz_snapshots if _before_cutoff(item.observed_at, cutoff)
    }
    known: dict[str, tuple[str, float | None, str]] = {
        "synopsis_embedding": (
            "mean-pooled BERT, 768 dimensions" if movie.synopsis else "title-only fallback",
            contributions.get("synopsis_embedding"),
            "Modeled directly by bert-xgb-v1.",
        ),
        "budget": (
            f"${budget:,.0f} ({budget_status.replace('_', ' ')})",
            contributions.get("log_budget"),
            "Log production budget is an original structured feature.",
        ),
        "genre": (
            ", ".join(_json(movie.genres_json, [])),
            genre_contribution,
            "Primary genre is one-hot encoded in the original model.",
        ),
        "director_history": (
            f"{director or 'unattached'}; {director_films} prior films",
            director_contribution,
            "Average, maximum, and count use the pre-2024 training history.",
        ),
        "release_month": (
            movie.release_date.strftime("%B") if movie.release_date else "unavailable",
            contributions.get("decade"),
            "Only release decade, not month, is represented in this baseline.",
        ),
        "nearby_competition": (
            f"{competition} confirmed films within 7 days",
            None,
            "Displayed as context; not scored by bert-xgb-v1.",
        ),
        "runtime": (
            f"{movie.runtime_minutes} min" if movie.runtime_minutes else "unavailable",
            None,
            "Not an input to bert-xgb-v1.",
        ),
        "certification": (
            movie.certification or "unavailable",
            None,
            "Not an input to bert-xgb-v1.",
        ),
        "origin_language": (
            " / ".join(item for item in [movie.origin_country, movie.original_language] if item)
            or "unavailable",
            None,
            "Not an input to bert-xgb-v1.",
        ),
        "google_momentum": (
            "collected" if "google_trends" in buzz_sources else "unavailable at cutoff",
            None,
            "Timestamped for successor models; no hand-authored multiplier is applied.",
        ),
        "wikipedia_attention": (
            "collected" if "wikimedia" in buzz_sources else "unavailable at cutoff",
            None,
            "Timestamped for successor models; not scored by this baseline.",
        ),
        "trailer_momentum": (
            "collected" if "youtube" in buzz_sources else "unavailable at cutoff",
            None,
            "Timestamped for successor models; not scored by this baseline.",
        ),
        "news_reddit_attention": (
            (
                "collected"
                if {"gdelt", "reddit"}.intersection(buzz_sources)
                else "unavailable at cutoff"
            ),
            None,
            "Only approved, timestamped aggregates are eligible.",
        ),
    }
    output: list[dict[str, object]] = []
    for key, label, group in PRODUCTION_FACTORS:
        value, impact, evidence = known.get(
            key,
            ("unavailable", None, "Not an input to bert-xgb-v1."),
        )
        direction = (
            "unknown"
            if impact is None
            else "positive"
            if impact > prediction.p50 * 0.005
            else "negative"
            if impact < -prediction.p50 * 0.005
            else "neutral"
        )
        output.append(
            {
                "key": key,
                "label": label,
                "group": group,
                "value": value,
                "impact": round(impact, 2) if impact is not None else None,
                "direction": direction,
                "evidence": evidence,
                "source_count": sum(
                    _before_cutoff(observation.observed_at, cutoff)
                    for observation in movie.observations
                ),
            }
        )
    return output


def _competition_count(db: Session, movie: Movie, cutoff: datetime) -> int:
    if movie.release_date is None:
        return 0
    candidates = db.scalars(
        select(Movie).where(
            Movie.id != movie.id,
            Movie.release_date.is_not(None),
            Movie.data_updated_at <= cutoff,
        )
    )
    return sum(
        abs((candidate.release_date - movie.release_date).days) <= 7
        for candidate in candidates
        if candidate.release_date
    )


def _comparables(
    db: Session,
    movie: Movie,
    budget: float,
    cutoff: datetime,
) -> list[dict[str, object]]:
    genres = set(_json(movie.genres_json, []))
    candidates = list(
        db.scalars(
            select(Movie).where(
                Movie.release_year <= cutoff.year,
                Movie.release_status.in_(["released", "gross_closed"]),
                Movie.id != movie.id,
            )
        )
    )
    scored = []
    for candidate in candidates:
        candidate_genres = set(_json(candidate.genres_json, []))
        overlap = len(genres.intersection(candidate_genres)) / max(
            1,
            len(genres.union(candidate_genres)),
        )
        budget_fit = (
            1 - min(1.0, abs(candidate.budget - budget) / max(budget, 1.0))
            if candidate.budget
            else 0.0
        )
        score = overlap * 0.72 + budget_fit * 0.28
        if score <= 0:
            continue
        actual = next(
            (item.amount for item in candidate.actual_grosses if item.target == "worldwide_total"),
            None,
        )
        scored.append(
            (
                score,
                {
                    "movie_id": candidate.id,
                    "slug": candidate.slug,
                    "title": candidate.title,
                    "release_year": candidate.release_year,
                    "similarity": round(score, 4),
                    "actual_worldwide": actual,
                    "reason": "Genre overlap and production-budget proximity.",
                },
            )
        )
    scored.sort(key=lambda item: (-item[0], item[1]["title"]))
    return [item[1] for item in scored[:5]]


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _before_cutoff(value: datetime, cutoff: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    return value <= cutoff
