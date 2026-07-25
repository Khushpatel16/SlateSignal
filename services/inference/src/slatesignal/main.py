from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slatesignal.api.routes import admin, auth, catalog, forecast, health, movies, projects
from slatesignal.core.config import get_settings
from slatesignal.core.database import Base, SessionLocal, engine
from slatesignal.core.observability import RequestObservabilityMiddleware
from slatesignal.domain import models as _models  # noqa: F401
from slatesignal.services.bootstrap import (
    bootstrap_historical_evaluations,
    bootstrap_holdout_evaluations,
    bootstrap_launch_forecasts,
    bootstrap_real_catalog,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        bootstrap_real_catalog(db)
        bootstrap_launch_forecasts(db)
        if settings.bootstrap_historical_evaluations:
            bootstrap_historical_evaluations(db)
        bootstrap_holdout_evaluations(db)
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(RequestObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for route in (
    health.router,
    auth.router,
    forecast.router,
    movies.router,
    catalog.router,
    projects.router,
    admin.router,
):
    app.include_router(route, prefix=settings.api_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "SlateSignal API", "docs": "/docs", "health": "/v1/health"}
