from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from slatesignal.core.database import get_db
from slatesignal.domain.schemas import UpcomingMovie
from slatesignal.services.movies import list_movies

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/upcoming", response_model=list[UpcomingMovie])
def upcoming(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=50, ge=1, le=100),
) -> list[UpcomingMovie]:
    catalog = list_movies(
        db,
        query=None,
        status=["confirmed", "date_tentative", "year_only", "in_theaters"],
        years=[],
        genre=None,
        forecast_ready=None,
        limit=limit,
        offset=0,
    )
    return [
        UpcomingMovie(
            id=movie.id,
            title=movie.title,
            release_date=movie.release_date,
            synopsis=movie.synopsis or "",
            genres=movie.genres,
            poster_url=movie.poster_url,
            backdrop_url=movie.backdrop_url,
            director=movie.director,
            cast=movie.top_cast,
            studio=movie.studio,
            data_source=(
                "tmdb"
                if movie.primary_source == "tmdb"
                else "research_corpus"
                if movie.primary_source == "research_corpus"
                else "official_seed"
            ),
            forecast_ready=movie.forecast.availability == "locked",
        )
        for movie in catalog.items
        if movie.release_date is not None
    ]
