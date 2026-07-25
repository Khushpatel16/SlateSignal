from pathlib import Path

from fastapi import APIRouter
from sqlalchemy import text

from slatesignal.api.dependencies import DbSession
from slatesignal.core.config import get_settings
from slatesignal.domain.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    settings = get_settings()
    db.execute(text("SELECT 1"))
    return HealthResponse(
        status="ok",
        version="0.1.0",
        model_mode="artifact" if settings.model_artifact_path else "decision_engine",
        database="postgresql" if settings.database_url.startswith("postgresql") else "sqlite",
        knowledge_base_loaded=Path(settings.knowledge_base_path).exists(),
        tmdb_configured=bool(settings.tmdb_api_token),
    )
