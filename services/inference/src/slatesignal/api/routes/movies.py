from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from slatesignal.core.database import get_db
from slatesignal.core.rate_limit import rate_limiter
from slatesignal.domain.schemas import (
    BacktestResponse,
    BuzzPoint,
    ForecastHistoryPoint,
    MovieDetail,
    MovieForecast,
    MovieListResponse,
)
from slatesignal.services.movies import (
    backtests,
    forecast_history,
    get_movie,
    latest_movie_forecast,
    list_movies,
    movie_buzz,
    movie_detail,
    serialize_forecast,
)

router = APIRouter(tags=["movies"])


@router.get(
    "/movies",
    response_model=MovieListResponse,
    dependencies=[Depends(rate_limiter.dependency(limit=120, window_seconds=60))],
)
def movies(
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    q: Annotated[str | None, Query(max_length=160)] = None,
    status: Annotated[list[str] | None, Query()] = None,
    year: Annotated[list[int] | None, Query()] = None,
    genre: Annotated[str | None, Query(max_length=64)] = None,
    forecast_ready: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MovieListResponse:
    result = list_movies(
        db,
        query=q,
        status=status or [],
        years=year or [],
        genre=genre,
        forecast_ready=forecast_ready,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = (
        "public, max-age=30, s-maxage=120, stale-while-revalidate=300"
    )
    return result


@router.get("/movies/{identifier}/forecast", response_model=MovieForecast)
def movie_forecast(
    identifier: str,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    cutoff: datetime | None = None,
    horizon_days: int | None = Query(default=None, ge=0, le=3650),
) -> MovieForecast:
    movie = get_movie(db, identifier)
    if cutoff is None and horizon_days is None:
        result = latest_movie_forecast(movie)
    else:
        candidates = [
            item
            for item in movie.forecasts
            if item.ledger_entry
            and (cutoff is None or item.data_cutoff <= cutoff)
            and (horizon_days is None or item.horizon_days == horizon_days)
        ]
        result = (
            serialize_forecast(
                movie,
                max(candidates, key=lambda item: item.data_cutoff),
            )
            if candidates
            else latest_movie_forecast(movie)
        )
    response.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=3600"
    )
    response.headers["ETag"] = f'"{result.ledger_hash}"'
    response.headers["X-Ledger-Hash"] = result.ledger_hash
    return result


@router.get(
    "/movies/{identifier}/forecast-history",
    response_model=list[ForecastHistoryPoint],
)
def movie_forecast_history(
    identifier: str,
    db: Annotated[Session, Depends(get_db)],
    response: Response,
) -> list[ForecastHistoryPoint]:
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300"
    return forecast_history(get_movie(db, identifier))


@router.get("/movies/{identifier}/buzz", response_model=list[BuzzPoint])
def movie_buzz_history(
    identifier: str,
    db: Annotated[Session, Depends(get_db)],
    cutoff: datetime | None = None,
) -> list[BuzzPoint]:
    return movie_buzz(get_movie(db, identifier), cutoff=cutoff)


@router.get("/movies/{identifier}", response_model=MovieDetail)
def movie(
    identifier: str,
    db: Annotated[Session, Depends(get_db)],
) -> MovieDetail:
    return movie_detail(get_movie(db, identifier))


@router.get("/backtests", response_model=BacktestResponse)
def backtest_index(
    db: Annotated[Session, Depends(get_db)],
    response: Response,
    cutoff: datetime | None = None,
    model_version: Annotated[str | None, Query(max_length=80)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BacktestResponse:
    result = backtests(
        db,
        cutoff=cutoff,
        model_version=model_version,
        limit=limit,
        offset=offset,
    )
    response.headers["Cache-Control"] = "public, max-age=60, s-maxage=300"
    return result
