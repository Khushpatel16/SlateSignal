from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.core.config import get_settings
from slatesignal.domain.models import (
    ActualGross,
    Company,
    Credit,
    ExternalIdentifier,
    ForecastRun,
    ModelVersion,
    Movie,
    MovieCompany,
    Person,
    Release,
)
from slatesignal.services.ledger import seal_forecast
from slatesignal.services.official_forecasts import ensure_research_model_version
from slatesignal.services.provenance import (
    canonical_json,
    payload_checksum,
    record_observation,
)


def bootstrap_real_catalog(db: Session) -> int:
    settings = get_settings()
    path = Path(settings.catalog_seed_path)
    if not settings.bootstrap_catalog or not path.exists():
        return 0

    payload = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for item in payload.get("movies", []):
        if _upsert_seed_movie(db, item):
            changed += 1
    db.commit()
    return changed


def bootstrap_holdout_evaluations(db: Session) -> int:
    """Load sealed retrospective holdout rows without requiring source notebooks."""

    path = Path(get_settings().holdout_evaluation_path)
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    model_version = ensure_research_model_version(db)
    cutoff = datetime.fromisoformat(payload["data_cutoff"])
    generated_at = datetime.fromisoformat(payload["generated_at"])
    feature_manifest_hash = hashlib.sha256(
        model_version.feature_manifest_json.encode("utf-8")
    ).hexdigest()
    created = 0

    for item in payload.get("rows", []):
        movie = db.scalar(
            select(Movie).where(
                Movie.title == item["title"],
                Movie.release_year == int(item["release_year"]),
            )
        )
        if movie is None:
            continue
        existing = db.scalar(
            select(ForecastRun).where(
                ForecastRun.movie_id == movie.id,
                ForecastRun.model_version_id == model_version.id,
                ForecastRun.data_cutoff == cutoff,
                ForecastRun.forecast_type == "evaluation",
            )
        )
        if existing is not None:
            seal_forecast(db, existing)
            continue

        eligible_evidence = [
            {
                "id": observation.id,
                "source": observation.source,
                "observed_at": observation.observed_at.isoformat(),
                "raw_checksum": observation.raw_checksum,
            }
            for observation in movie.observations
            if _before_or_at(observation.observed_at, cutoff) and observation.forecast_eligible
        ]
        eligible_evidence.append(
            {
                "source": "research_holdout_artifact",
                "feature_vector_sha256": item["feature_vector_sha256"],
                "source_checksums": payload["source_checksums"],
            }
        )
        forecast = ForecastRun(
            movie_id=movie.id,
            model_version_id=model_version.id,
            data_cutoff=cutoff,
            horizon_days=None,
            forecast_type="evaluation",
            targets_json=canonical_json(item["targets"]),
            factors_json=canonical_json(item["factors"]),
            buzz_json="[]",
            comparables_json="[]",
            fairness_json=canonical_json(
                {
                    "protected_attributes_used": False,
                    "audit_status": "insufficient_data",
                    "evaluation_only_attributes": ["Wikidata demographic annotations"],
                    "cohort_definition": (
                        "Matched budget, genre, and release-year cohorts with "
                        "bootstrap confidence intervals; evaluation only."
                    ),
                    "notes": [
                        "No protected attributes are model inputs.",
                        "The original name-derived binary gender analysis is rejected.",
                        "This 24-film slice is too small for a powered subgroup audit.",
                    ],
                }
            ),
            evidence_manifest_json=canonical_json(eligible_evidence),
            confidence_score=0.42,
            feature_manifest_hash=feature_manifest_hash,
            limitations_json=canonical_json(
                [
                    payload["methodology_note"],
                    "Only worldwide gross is available for this research baseline.",
                    "Pre-release buzz and distribution-scale observations are unavailable.",
                    "The research corpus is popularity-selected rather than a census.",
                ]
            ),
            generated_at=generated_at,
        )
        db.add(forecast)
        db.flush()
        seal_forecast(db, forecast)
        created += 1

    db.commit()
    return created


def bootstrap_historical_evaluations(db: Session) -> int:
    """Load sealed retrospective temporal folds for released 2021-2024 films."""

    path = Path(get_settings().historical_evaluation_path)
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    generated_at = datetime.fromisoformat(payload["generated_at"])
    versions = {
        item["version"]: _ensure_evaluation_model_version(db, item)
        for item in payload.get("model_versions", [])
    }
    created = 0

    for item in payload.get("rows", []):
        movie = db.scalar(
            select(Movie).where(
                Movie.title == item["title"],
                Movie.release_year == int(item["release_year"]),
            )
        )
        model_version = versions.get(item["model_version"])
        if movie is None or model_version is None:
            continue
        cutoff = datetime.fromisoformat(item["data_cutoff"])
        horizon_days = (movie.release_date - cutoff.date()).days if movie.release_date else None
        existing = db.scalar(
            select(ForecastRun).where(
                ForecastRun.movie_id == movie.id,
                ForecastRun.model_version_id == model_version.id,
                ForecastRun.data_cutoff == cutoff,
                ForecastRun.horizon_days == horizon_days,
                ForecastRun.forecast_type == "evaluation",
            )
        )
        if existing is not None:
            seal_forecast(db, existing)
            continue

        feature_manifest_hash = hashlib.sha256(
            model_version.feature_manifest_json.encode("utf-8")
        ).hexdigest()
        evidence = [
            {
                "source": "retrospective_temporal_fold_artifact",
                "feature_vector_sha256": item["feature_vector_sha256"],
                "source_checksums": payload["source_checksums"],
                "simulated_cutoff": item["data_cutoff"],
                "generated_at": payload["generated_at"],
                "is_ex_ante": False,
            }
        ]
        forecast = ForecastRun(
            movie_id=movie.id,
            model_version_id=model_version.id,
            data_cutoff=cutoff,
            horizon_days=horizon_days,
            forecast_type="evaluation",
            targets_json=canonical_json(item["targets"]),
            factors_json=canonical_json(item["factors"]),
            buzz_json="[]",
            comparables_json="[]",
            fairness_json=canonical_json(
                {
                    "protected_attributes_used": False,
                    "audit_status": "insufficient_data",
                    "evaluation_only_attributes": ["Wikidata demographic annotations"],
                    "cohort_definition": (
                        "Matched budget, genre, and release-year cohorts with "
                        "bootstrap confidence intervals; evaluation only."
                    ),
                    "notes": [
                        "No protected attributes are model inputs.",
                        "The temporal fold does not reuse target-year revenue.",
                        "This individual fold is not a powered subgroup audit.",
                    ],
                }
            ),
            evidence_manifest_json=canonical_json(evidence),
            confidence_score=0.4,
            feature_manifest_hash=feature_manifest_hash,
            limitations_json=canonical_json([payload["methodology_note"], *payload["limitations"]]),
            generated_at=generated_at,
        )
        db.add(forecast)
        db.flush()
        seal_forecast(db, forecast)
        created += 1

    db.commit()
    return created


def _ensure_evaluation_model_version(
    db: Session,
    item: dict[str, Any],
) -> ModelVersion:
    model_version = db.scalar(select(ModelVersion).where(ModelVersion.version == item["version"]))
    feature_manifest = canonical_json(item["feature_manifest"])
    if model_version is not None:
        model_version.artifact_uri = item["artifact_uri"]
        model_version.artifact_checksum = item["artifact_checksum"]
        model_version.feature_manifest_json = feature_manifest
        model_version.metrics_json = canonical_json(item["metrics"])
        return model_version
    model_version = ModelVersion(
        version=item["version"],
        display_name=item["display_name"],
        model_kind=item["model_kind"],
        artifact_uri=item["artifact_uri"],
        artifact_checksum=item["artifact_checksum"],
        feature_manifest_json=feature_manifest,
        metrics_json=canonical_json(item["metrics"]),
        training_cutoff=date.fromisoformat(item["training_cutoff"]),
        promoted=False,
    )
    db.add(model_version)
    db.flush()
    return model_version


def bootstrap_launch_forecasts(db: Session) -> int:
    """Load portable official launch forecasts and seal them in this database."""

    path = Path(get_settings().launch_forecasts_path)
    if not path.exists():
        return 0
    payload = json.loads(path.read_text(encoding="utf-8"))
    model_version = ensure_research_model_version(db)
    expected_manifest_hash = hashlib.sha256(
        model_version.feature_manifest_json.encode("utf-8")
    ).hexdigest()
    created = 0
    for item in payload.get("rows", []):
        movie = db.scalar(select(Movie).where(Movie.slug == item["movie"]["slug"]))
        if movie is None:
            continue
        if item["feature_manifest_hash"] != expected_manifest_hash:
            raise ValueError("Launch forecast feature manifest is stale")
        cutoff = datetime.fromisoformat(item["data_cutoff"])
        existing = db.scalar(
            select(ForecastRun).where(
                ForecastRun.movie_id == movie.id,
                ForecastRun.model_version_id == model_version.id,
                ForecastRun.data_cutoff == cutoff,
                ForecastRun.horizon_days == item["horizon_days"],
                ForecastRun.forecast_type == "official",
            )
        )
        if existing is not None:
            seal_forecast(db, existing)
            continue
        comparables = []
        for comparable in item.get("comparables", []):
            comparable_movie = db.scalar(select(Movie).where(Movie.slug == comparable["slug"]))
            normalized = dict(comparable)
            if comparable_movie is not None:
                normalized["movie_id"] = comparable_movie.id
            comparables.append(normalized)
        evidence = [
            {
                "id": observation.id,
                "source": observation.source,
                "observed_at": observation.observed_at.isoformat(),
                "raw_checksum": observation.raw_checksum,
            }
            for observation in movie.observations
            if _before_or_at(observation.observed_at, cutoff) and observation.forecast_eligible
        ]
        forecast = ForecastRun(
            movie_id=movie.id,
            model_version_id=model_version.id,
            data_cutoff=cutoff,
            horizon_days=item["horizon_days"],
            forecast_type="official",
            targets_json=canonical_json(item["targets"]),
            factors_json=canonical_json(item["factors"]),
            buzz_json=canonical_json(item["buzz"]),
            comparables_json=canonical_json(comparables),
            fairness_json=canonical_json(item["fairness"]),
            evidence_manifest_json=canonical_json(evidence),
            confidence_score=float(item["confidence_score"]),
            feature_manifest_hash=item["feature_manifest_hash"],
            limitations_json=canonical_json(item["limitations"]),
            generated_at=datetime.fromisoformat(item["generated_at"]),
        )
        db.add(forecast)
        db.flush()
        seal_forecast(db, forecast)
        created += 1
    db.commit()
    return created


def _upsert_seed_movie(db: Session, item: dict[str, Any]) -> bool:
    movie = db.scalar(select(Movie).where(Movie.slug == item["slug"]))
    created = movie is None
    observed_at = datetime.fromisoformat(item["observed_at"])
    release_date = date.fromisoformat(item["release_date"]) if item.get("release_date") else None
    if movie is None:
        movie = Movie(
            slug=item["slug"],
            title=item["title"],
            original_title=item.get("original_title"),
            synopsis=item.get("synopsis"),
            release_status=item["release_status"],
            release_date=release_date,
            release_year=int(item["release_year"]),
            date_precision=item.get("date_precision", "day"),
            runtime_minutes=_runtime_minutes(item.get("runtime")),
            certification=item.get("certification"),
            original_language=item.get("original_language", "en"),
            origin_country=item.get("origin_country", "US"),
            genres_json=json.dumps(item.get("genres", [])),
            budget=item.get("budget"),
            budget_status=item.get("budget_status", "unavailable"),
            poster_url=item.get("poster_url"),
            backdrop_url=item.get("backdrop_url"),
            trailer_url=item.get("trailer_url"),
            homepage_url=item.get("homepage_url"),
            primary_source=item["source"],
            source_confidence=float(item.get("source_confidence", 0.5)),
            data_updated_at=observed_at,
        )
        db.add(movie)
        db.flush()
    elif movie.primary_source in {"research_corpus", "sony_pictures", "marvel", "legendary"}:
        movie.release_status = item["release_status"]
        movie.release_date = release_date
        movie.release_year = int(item["release_year"])
        movie.date_precision = item.get("date_precision", movie.date_precision)
        current_updated_at = movie.data_updated_at
        if current_updated_at.tzinfo is None:
            current_updated_at = current_updated_at.replace(tzinfo=observed_at.tzinfo)
        movie.data_updated_at = max(current_updated_at, observed_at)
        movie.source_confidence = max(
            movie.source_confidence,
            float(item.get("source_confidence", 0.5)),
        )
        if not movie.synopsis:
            movie.synopsis = item.get("synopsis")
        if not movie.trailer_url:
            movie.trailer_url = item.get("trailer_url")
        if not movie.poster_url:
            movie.poster_url = item.get("poster_url")
        if not movie.backdrop_url:
            movie.backdrop_url = item.get("backdrop_url")

    observation = record_observation(
        db,
        movie_id=movie.id,
        source=item["source"],
        observation_type="catalog_snapshot",
        observed_at=observed_at,
        source_url=item["source_url"],
        confidence=float(item.get("source_confidence", 0.5)),
        payload=item,
    )

    for source, external_id in item.get("external_ids", {}).items():
        if not external_id:
            continue
        existing = db.scalar(
            select(ExternalIdentifier).where(
                ExternalIdentifier.source == source,
                ExternalIdentifier.external_id == external_id,
            )
        )
        if existing is None:
            db.add(
                ExternalIdentifier(
                    movie_id=movie.id,
                    source=source,
                    external_id=external_id,
                    source_url=(
                        f"https://www.imdb.com/title/{external_id}/" if source == "imdb" else None
                    ),
                )
            )

    people: list[tuple[str, str, int | None]] = []
    if item.get("director"):
        people.append((item["director"], "Director", None))
    people.extend((name, "Director", None) for name in item.get("additional_directors", []))
    people.extend((name, "Actor", index) for index, name in enumerate(item.get("cast", [])))
    unique_people = list(dict.fromkeys(people))
    for name, role, order in unique_people:
        person = _person(db, item["source"], name)
        department = "Directing" if role == "Director" else "Acting"
        credit_exists = db.scalar(
            select(Credit).where(
                Credit.movie_id == movie.id,
                Credit.person_id == person.id,
                Credit.department == department,
                Credit.job == role,
                Credit.character_name == "",
            )
        )
        if credit_exists is None:
            db.add(
                Credit(
                    movie_id=movie.id,
                    person_id=person.id,
                    department=department,
                    job=role,
                    character_name="",
                    billing_order=order,
                )
            )

    for company_name in dict.fromkeys(item.get("companies", [])):
        company = _company(db, item["source"], company_name)
        company_link_exists = db.scalar(
            select(MovieCompany).where(
                MovieCompany.movie_id == movie.id,
                MovieCompany.company_id == company.id,
                MovieCompany.role == "production",
            )
        )
        if company_link_exists is None:
            db.add(
                MovieCompany(
                    movie_id=movie.id,
                    company_id=company.id,
                    role="production",
                )
            )

    if release_date:
        release = db.scalar(
            select(Release).where(
                Release.movie_id == movie.id,
                Release.country_code == "US",
                Release.release_type == "theatrical",
                Release.release_date == release_date,
            )
        )
        if release is None:
            db.add(
                Release(
                    movie_id=movie.id,
                    country_code="US",
                    release_type="theatrical",
                    release_date=release_date,
                    certification=item.get("certification"),
                    note=None,
                    is_confirmed=item["release_status"] != "date_tentative",
                    source_observation_id=observation.id,
                )
            )

    for actual in item.get("actuals", []):
        checksum = payload_checksum(actual)
        actual_exists = db.scalar(
            select(ActualGross).where(
                ActualGross.movie_id == movie.id,
                ActualGross.target == actual["target"],
                ActualGross.source == item["source"],
                ActualGross.observed_at == observed_at,
            )
        )
        if actual_exists is None:
            db.add(
                ActualGross(
                    movie_id=movie.id,
                    target=actual["target"],
                    amount=float(actual["amount"]),
                    currency=actual.get("currency", "USD"),
                    amount_status=actual.get("amount_status", "provisional"),
                    source=item["source"],
                    source_url=item["source_url"],
                    confidence=float(item.get("source_confidence", 0.5)),
                    observed_at=observed_at,
                    raw_checksum=checksum,
                    conflict_group=f"{movie.id}:{actual['target']}",
                )
            )
    return created


def _stable_source_id(source: str, value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    digest = hashlib.sha256(f"{source}:{normalized}".encode()).hexdigest()[:24]
    return f"seed-{digest}"


def _person(db: Session, source: str, name: str) -> Person:
    source_id = _stable_source_id(source, name)
    person = db.scalar(select(Person).where(Person.source == source, Person.source_id == source_id))
    if person is None:
        person = Person(name=name, source=source, source_id=source_id)
        db.add(person)
        db.flush()
    return person


def _company(db: Session, source: str, name: str) -> Company:
    source_id = _stable_source_id(source, name)
    company = db.scalar(
        select(Company).where(Company.source == source, Company.source_id == source_id)
    )
    if company is None:
        company = Company(name=name, source=source, source_id=source_id)
        db.add(company)
        db.flush()
    return company


def _runtime_minutes(value: str | None) -> int | None:
    if not value:
        return None
    hours = re.search(r"(\d+)\s*h", value)
    minutes = re.search(r"(\d+)\s*m", value)
    total = (int(hours.group(1)) * 60 if hours else 0) + (int(minutes.group(1)) if minutes else 0)
    return total or None


def _before_or_at(value: datetime, cutoff: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    return value <= cutoff
