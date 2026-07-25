from typing import Annotated

from fastapi import APIRouter, Depends, Query

from slatesignal.core.rate_limit import rate_limiter
from slatesignal.domain.schemas import (
    CatalogSearchResponse,
    ForecastRequest,
    ForecastResponse,
    Genre,
    OptimizeRequest,
    OptimizeResponse,
)
from slatesignal.services.forecast import ForecastEngine
from slatesignal.services.knowledge import get_knowledge_base
from slatesignal.services.optimizer import GreenlightOptimizer

router = APIRouter(tags=["forecast"])


@router.post(
    "/scenarios/forecast",
    response_model=ForecastResponse,
    dependencies=[Depends(rate_limiter.dependency(limit=40, window_seconds=60))],
)
def forecast(payload: ForecastRequest) -> ForecastResponse:
    return ForecastEngine().predict(payload)


@router.post(
    "/scenarios/optimize",
    response_model=OptimizeResponse,
    dependencies=[Depends(rate_limiter.dependency(limit=10, window_seconds=60))],
)
def optimize(payload: OptimizeRequest) -> OptimizeResponse:
    return GreenlightOptimizer().optimize(payload)


@router.get("/scenarios/catalog/search", response_model=CatalogSearchResponse)
def catalog_search(
    q: Annotated[str, Query(max_length=120)] = "",
    genres: Annotated[list[Genre] | None, Query()] = None,
) -> CatalogSearchResponse:
    return get_knowledge_base().search(q, genres or [], limit=8)
