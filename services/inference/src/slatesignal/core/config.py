from datetime import date
from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SlateSignal API"
    environment: str = "development"
    api_prefix: str = "/v1"
    database_url: str = f"sqlite:///{SERVICE_ROOT / 'data' / 'slatesignal.db'}"
    web_origin: str = "http://localhost:3000"
    cookie_name: str = "slatesignal_session"
    cookie_secure: bool = False
    session_days: int = Field(default=14, ge=1, le=90)
    auto_create_schema: bool = True
    admin_email: str | None = None
    admin_bootstrap_token: str | None = None
    tmdb_api_token: str | None = None
    youtube_api_key: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "SlateSignal/0.2 research@localhost"
    google_trends_api_key: str | None = None
    imdb_cache_dir: str = str(Path(gettempdir()) / "slatesignal-imdb")
    gcp_project_id: str | None = None
    gcs_model_bucket: str | None = None
    model_artifact_path: str = str(SERVICE_ROOT / "artifacts" / "bert-xgb-v1.ubj")
    model_manifest_path: str = str(SERVICE_ROOT / "artifacts" / "bert-xgb-v1.json")
    director_history_path: str = str(SERVICE_ROOT / "artifacts" / "director-history-v1.json")
    bert_model_name: str = "bert-base-uncased"
    bert_onnx_path: str = str(SERVICE_ROOT / "artifacts" / "bert-base-uncased-fp16.onnx")
    bert_tokenizer_path: str = str(SERVICE_ROOT / "artifacts" / "bert-tokenizer")
    knowledge_base_path: str = str(SERVICE_ROOT / "data" / "knowledge_base.json")
    catalog_seed_path: str = str(SERVICE_ROOT / "data" / "real_film_seed.json")
    historical_evaluation_path: str = str(SERVICE_ROOT / "data" / "historical_evaluations.json")
    holdout_evaluation_path: str = str(SERVICE_ROOT / "data" / "holdout_2025_evaluation.json")
    launch_forecasts_path: str = str(SERVICE_ROOT / "data" / "launch_forecasts.json")
    bootstrap_catalog: bool = True
    bootstrap_historical_evaluations: bool = True
    catalog_start_date: date = date(2021, 1, 1)
    catalog_end_date: date = date(2030, 12, 31)
    request_timeout_seconds: float = Field(default=20.0, ge=2.0, le=120.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
