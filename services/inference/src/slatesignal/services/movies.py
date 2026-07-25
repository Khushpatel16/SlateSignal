from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from statistics import mean, median
from typing import Any

from fastapi import HTTPException
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, selectinload

from slatesignal.domain.models import (
    ActualGross,
    Credit,
    ForecastRun,
    Movie,
    MovieCompany,
    SourceObservation,
)
from slatesignal.domain.schemas import (
    ActualGrossPublic,
    BacktestMetrics,
    BacktestRecord,
    BacktestResponse,
    BuzzPoint,
    CompanyPublic,
    ComparableFilm,
    CreditPublic,
    EvidenceRecord,
    ExternalIdPublic,
    ForecastAvailability,
    ForecastBadge,
    ForecastFactor,
    ForecastFairness,
    ForecastHistoryPoint,
    MoneyInterval,
    MovieDetail,
    MovieForecast,
    MovieListResponse,
    MovieSummary,
    ReleasePublic,
    ReleaseStatus,
)


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return fallback


def _movie_options() -> tuple[Any, ...]:
    return (
        selectinload(Movie.external_ids),
        selectinload(Movie.credits).selectinload(Credit.person),
        selectinload(Movie.companies).selectinload(MovieCompany.company),
        selectinload(Movie.releases),
        selectinload(Movie.observations),
        selectinload(Movie.buzz_snapshots),
        selectinload(Movie.actual_grosses),
        selectinload(Movie.forecasts).selectinload(ForecastRun.model_version),
        selectinload(Movie.forecasts).selectinload(ForecastRun.ledger_entry),
    )


def movie_query() -> Select[tuple[Movie]]:
    return select(Movie).options(*_movie_options())


def get_movie(db: Session, identifier: str) -> Movie:
    movie = db.scalar(movie_query().where(or_(Movie.id == identifier, Movie.slug == identifier)))
    if movie is None:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


def list_movies(
    db: Session,
    *,
    query: str | None,
    status: list[str],
    years: list[int],
    genre: str | None,
    forecast_ready: bool | None,
    limit: int,
    offset: int,
) -> MovieListResponse:
    conditions: list[Any] = []
    if query:
        needle = f"%{query.strip()}%"
        conditions.append(or_(Movie.title.ilike(needle), Movie.original_title.ilike(needle)))
    if status:
        conditions.append(Movie.release_status.in_(status))
    if years:
        conditions.append(Movie.release_year.in_(years))
    if genre:
        conditions.append(Movie.genres_json.ilike(f'%"{genre}"%'))
    if forecast_ready is True:
        conditions.append(Movie.forecasts.any())
    elif forecast_ready is False:
        conditions.append(~Movie.forecasts.any())

    count_statement = select(func.count(Movie.id))
    statement = movie_query()
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    statement = statement.order_by(
        Movie.release_date.is_(None),
        Movie.release_date.asc(),
        Movie.title.asc(),
    )
    movies = list(db.scalars(statement.offset(offset).limit(limit)).unique())
    updated = max((movie.data_updated_at for movie in movies), default=None)
    return MovieListResponse(
        items=[movie_summary(movie) for movie in movies],
        total=int(db.scalar(count_statement) or 0),
        limit=limit,
        offset=offset,
        data_freshness=updated,
    )


def _latest_forecast(movie: Movie) -> ForecastRun | None:
    locked = [forecast for forecast in movie.forecasts if forecast.ledger_entry]
    if not locked:
        return None
    return max(locked, key=lambda item: (item.data_cutoff, item.generated_at))


def _personnel(movie: Movie) -> tuple[str | None, list[str]]:
    director = next(
        (
            credit.person.name
            for credit in movie.credits
            if credit.job.casefold() == "director" or credit.department.casefold() == "directing"
        ),
        None,
    )
    cast_credits = [
        credit for credit in movie.credits if credit.department.casefold() in {"acting", "cast"}
    ]
    cast_credits.sort(
        key=lambda item: item.billing_order if item.billing_order is not None else 99_999
    )
    return director, [credit.person.name for credit in cast_credits[:5]]


def _studio(movie: Movie) -> str | None:
    production = next(
        (link.company.name for link in movie.companies if link.role == "production"),
        None,
    )
    return production or (movie.companies[0].company.name if movie.companies else None)


def _actual(movie: Movie, target: str) -> ActualGrossPublic | None:
    candidates = [gross for gross in movie.actual_grosses if gross.target == target]
    if not candidates:
        return None

    latest_by_source: dict[str, ActualGross] = {}
    for gross in sorted(candidates, key=lambda item: item.observed_at):
        latest_by_source[gross.source] = gross
    current = list(latest_by_source.values())
    selected = max(current, key=lambda item: (item.confidence, item.observed_at))
    values = [item.amount for item in current]
    conflict = len(values) > 1 and (max(values) - min(values)) / max(1.0, median(values)) > 0.03
    return ActualGrossPublic(
        target=target,
        amount=selected.amount,
        currency=selected.currency,
        amount_status="conflicted" if conflict else selected.amount_status,
        source=selected.source,
        source_url=selected.source_url,
        observed_at=selected.observed_at,
        confidence=selected.confidence,
        conflicts=sorted({value for value in values if value != selected.amount}),
    )


def movie_summary(movie: Movie) -> MovieSummary:
    director, cast = _personnel(movie)
    forecast = _latest_forecast(movie)
    badge = ForecastBadge(availability=ForecastAvailability.PENDING)
    if forecast and forecast.ledger_entry:
        worldwide = _target(_json(forecast.targets_json, {}), "worldwide_total")
        badge = ForecastBadge(
            availability=ForecastAvailability.LOCKED,
            p10=worldwide.p10 if worldwide else None,
            p50=worldwide.p50 if worldwide else None,
            p90=worldwide.p90 if worldwide else None,
            horizon_days=forecast.horizon_days,
            data_cutoff=forecast.data_cutoff,
            model_version=forecast.model_version.version,
            ledger_hash=forecast.ledger_entry.ledger_hash,
        )
    elif not movie.synopsis:
        badge = ForecastBadge(availability=ForecastAvailability.UNAVAILABLE)

    today = datetime.now(UTC).date()
    countdown = (movie.release_date - today).days if movie.release_date else None
    latest_buzz = max(movie.buzz_snapshots, key=lambda item: item.observed_at, default=None)
    return MovieSummary(
        id=movie.id,
        slug=movie.slug,
        title=movie.title,
        original_title=movie.original_title,
        synopsis=movie.synopsis,
        release_status=ReleaseStatus(movie.release_status),
        release_date=movie.release_date,
        release_year=movie.release_year,
        date_precision=movie.date_precision,
        countdown_days=countdown,
        genres=_json(movie.genres_json, []),
        runtime_minutes=movie.runtime_minutes,
        certification=movie.certification,
        original_language=movie.original_language,
        origin_country=movie.origin_country,
        poster_url=movie.poster_url,
        backdrop_url=movie.backdrop_url,
        trailer_url=movie.trailer_url,
        director=director,
        top_cast=cast,
        studio=_studio(movie),
        forecast=badge,
        worldwide_actual=_actual(movie, "worldwide_total"),
        buzz_momentum=latest_buzz.momentum if latest_buzz else None,
        data_updated_at=movie.data_updated_at,
        primary_source=movie.primary_source,
        source_confidence=movie.source_confidence,
    )


def movie_detail(movie: Movie) -> MovieDetail:
    summary = movie_summary(movie)
    credits = sorted(
        movie.credits,
        key=lambda item: (
            item.department != "Acting",
            item.billing_order if item.billing_order is not None else 99_999,
            item.person.name,
        ),
    )
    return MovieDetail(
        **summary.model_dump(),
        budget=movie.budget,
        budget_status=movie.budget_status,
        homepage_url=movie.homepage_url,
        external_ids=[
            ExternalIdPublic(
                source=item.source,
                external_id=item.external_id,
                source_url=item.source_url,
            )
            for item in sorted(movie.external_ids, key=lambda item: item.source)
        ],
        credits=[
            CreditPublic(
                person_id=item.person.id,
                name=item.person.name,
                department=item.department,
                job=item.job,
                character_name=item.character_name,
                billing_order=item.billing_order,
                image_url=item.person.image_url,
            )
            for item in credits
        ],
        companies=[
            CompanyPublic(
                id=item.company.id,
                name=item.company.name,
                role=item.role,
                logo_url=item.company.logo_url,
            )
            for item in movie.companies
        ],
        releases=[
            ReleasePublic(
                country_code=item.country_code,
                release_type=item.release_type,
                release_date=item.release_date,
                certification=item.certification,
                note=item.note,
                is_confirmed=item.is_confirmed,
            )
            for item in sorted(movie.releases, key=lambda item: item.release_date)
        ],
        actuals=[
            actual
            for target in {item.target for item in movie.actual_grosses}
            if (actual := _actual(movie, target)) is not None
        ],
        evidence=[
            _evidence(item)
            for item in sorted(
                movie.observations,
                key=lambda item: item.observed_at,
                reverse=True,
            )
        ],
    )


def _evidence(observation: SourceObservation) -> EvidenceRecord:
    return EvidenceRecord(
        source=observation.source,
        observation_type=observation.observation_type,
        observed_at=observation.observed_at,
        source_url=observation.source_url,
        confidence=observation.confidence,
        raw_checksum=observation.raw_checksum,
        forecast_eligible=observation.forecast_eligible,
    )


def _target(payload: dict[str, Any], key: str) -> MoneyInterval | None:
    value = payload.get(key)
    if not isinstance(value, dict):
        return None
    try:
        return MoneyInterval.model_validate(value)
    except ValueError:
        return None


def _actual_map(movie: Movie) -> dict[str, ActualGrossPublic | None]:
    targets = {
        "worldwide_total",
        "domestic_total",
        "domestic_opening",
        "international_total",
    }
    return {target: _actual(movie, target) for target in targets}


def serialize_forecast(movie: Movie, forecast: ForecastRun) -> MovieForecast:
    if forecast.ledger_entry is None:
        raise HTTPException(status_code=409, detail="Forecast has not been sealed")
    targets_payload = _json(forecast.targets_json, {})
    targets = {
        key: _target(targets_payload, key)
        for key in {
            "worldwide_total",
            "domestic_total",
            "domestic_opening",
            "international_total",
        }
    }
    actuals = _actual_map(movie)
    errors: dict[str, float | None] = {}
    for key, interval in targets.items():
        actual = actuals[key]
        errors[key] = (
            abs(interval.p50 - actual.amount)
            if interval is not None and actual is not None
            else None
        )

    factors = [ForecastFactor.model_validate(item) for item in _json(forecast.factors_json, [])]
    buzz = [BuzzPoint.model_validate(item) for item in _json(forecast.buzz_json, [])]
    comparables = [
        ComparableFilm.model_validate(item) for item in _json(forecast.comparables_json, [])
    ]
    fairness = ForecastFairness.model_validate(_json(forecast.fairness_json, {}))
    evidence = [
        _evidence(item)
        for item in sorted(movie.observations, key=lambda item: item.observed_at)
        if _before_cutoff(item.observed_at, forecast.data_cutoff) and item.forecast_eligible
    ]
    return MovieForecast(
        film=movie_summary(movie),
        forecast_type=forecast.forecast_type,
        data_cutoff=forecast.data_cutoff,
        horizon_days=forecast.horizon_days,
        model_version=forecast.model_version.version,
        model_kind=forecast.model_version.model_kind,
        targets=targets,
        actuals=actuals,
        errors=errors,
        grouped_factors=factors,
        buzz=buzz,
        comparables=comparables,
        fairness=fairness,
        evidence=evidence,
        confidence_score=forecast.confidence_score,
        feature_manifest_hash=forecast.feature_manifest_hash,
        ledger_hash=forecast.ledger_entry.ledger_hash,
        ledger_sequence=forecast.ledger_entry.sequence,
        generated_at=forecast.generated_at,
        limitations=_json(forecast.limitations_json, []),
    )


def latest_movie_forecast(movie: Movie) -> MovieForecast:
    forecast = _latest_forecast(movie)
    if forecast is None:
        raise HTTPException(
            status_code=404,
            detail="No locked forecast is available for this film yet",
        )
    return serialize_forecast(movie, forecast)


def forecast_history(movie: Movie) -> list[ForecastHistoryPoint]:
    actual = _actual(movie, "worldwide_total")
    output = []
    for forecast in sorted(movie.forecasts, key=lambda item: item.data_cutoff):
        if forecast.ledger_entry is None:
            continue
        output.append(
            ForecastHistoryPoint(
                forecast_id=forecast.id,
                forecast_type=forecast.forecast_type,
                data_cutoff=forecast.data_cutoff,
                horizon_days=forecast.horizon_days,
                worldwide=_target(_json(forecast.targets_json, {}), "worldwide_total"),
                actual_worldwide=actual.amount if actual else None,
                model_version=forecast.model_version.version,
                ledger_hash=forecast.ledger_entry.ledger_hash,
                generated_at=forecast.generated_at,
            )
        )
    return output


def movie_buzz(movie: Movie, *, cutoff: datetime | None = None) -> list[BuzzPoint]:
    snapshots = movie.buzz_snapshots
    if cutoff:
        snapshots = [item for item in snapshots if _before_cutoff(item.observed_at, cutoff)]
    return [
        BuzzPoint(
            source=item.source,
            metric=item.metric,
            value=item.value,
            normalized_value=item.normalized_value,
            momentum=item.momentum,
            observed_at=item.observed_at,
            source_url=item.source_url,
            confidence=item.confidence,
        )
        for item in sorted(snapshots, key=lambda item: item.observed_at)
    ]


def backtests(
    db: Session,
    *,
    cutoff: datetime | None,
    model_version: str | None,
    limit: int,
    offset: int,
) -> BacktestResponse:
    statement = movie_query().where(Movie.release_status.in_(["released", "gross_closed"]))
    movies = list(db.scalars(statement.order_by(Movie.release_date.desc())).unique())
    records: list[BacktestRecord] = []
    for movie in movies:
        candidates = [
            item
            for item in movie.forecasts
            if item.ledger_entry
            and (cutoff is None or item.data_cutoff <= cutoff)
            and (model_version is None or item.model_version.version == model_version)
        ]
        if not candidates:
            continue
        forecast = max(candidates, key=lambda item: item.data_cutoff)
        history = next(item for item in forecast_history(movie) if item.forecast_id == forecast.id)
        actual = _actual(movie, "worldwide_total")
        absolute_error = (
            abs(history.worldwide.p50 - actual.amount) if history.worldwide and actual else None
        )
        percentage_error = (
            absolute_error / actual.amount
            if absolute_error is not None and actual and actual.amount > 0
            else None
        )
        records.append(
            BacktestRecord(
                movie=movie_summary(movie),
                forecast=history,
                actual_worldwide=actual,
                absolute_error=absolute_error,
                absolute_percentage_error=percentage_error,
            )
        )

    visible = records[offset : offset + limit]
    errors = [item.absolute_error for item in records if item.absolute_error is not None]
    log_errors = [
        abs(math.log1p(item.forecast.worldwide.p50) - math.log1p(item.actual_worldwide.amount))
        for item in records
        if item.forecast.worldwide and item.actual_worldwide
    ]
    covered = [
        item.forecast.worldwide.p10 <= item.actual_worldwide.amount <= item.forecast.worldwide.p90
        for item in records
        if item.forecast.worldwide and item.actual_worldwide
    ]
    return BacktestResponse(
        items=visible,
        metrics=BacktestMetrics(
            count=len(records),
            mae=mean(errors) if errors else None,
            median_absolute_error=median(errors) if errors else None,
            log_mae=mean(log_errors) if log_errors else None,
            interval_coverage=mean(covered) if covered else None,
        ),
        cutoff=cutoff,
        model_version=model_version,
        methodology_note=(
            "Only sealed forecasts are scored. Feature evidence is restricted to records "
            "observed on or before each forecast cutoff. Retrospective evaluation forecasts "
            "are labeled separately from forecasts created before public release."
        ),
    )


def _before_cutoff(value: datetime, cutoff: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=UTC)
    return value <= cutoff
