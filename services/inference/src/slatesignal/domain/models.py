from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from slatesignal.core.database import Base


def _uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(80))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    sessions: Mapped[list["AuthSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["SavedProject"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship(back_populates="sessions")


class SavedProject(Base):
    __tablename__ = "saved_projects"
    __table_args__ = (Index("ix_saved_projects_user_updated", "user_id", "updated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    project_type: Mapped[str] = mapped_column(String(32), default="scenario")
    payload_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    user: Mapped[User] = relationship(back_populates="projects")


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        Index("ix_movies_release_status_date", "release_status", "release_date"),
        Index("ix_movies_release_year_title", "release_year", "title"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    original_title: Mapped[str | None] = mapped_column(String(300))
    synopsis: Mapped[str | None] = mapped_column(Text)
    release_status: Mapped[str] = mapped_column(String(32), index=True)
    release_date: Mapped[date | None] = mapped_column(Date, index=True)
    release_year: Mapped[int] = mapped_column(Integer, index=True)
    date_precision: Mapped[str] = mapped_column(String(16), default="day")
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    certification: Mapped[str | None] = mapped_column(String(24))
    original_language: Mapped[str | None] = mapped_column(String(16))
    origin_country: Mapped[str | None] = mapped_column(String(8))
    genres_json: Mapped[str] = mapped_column(Text, default="[]")
    budget: Mapped[float | None] = mapped_column(Float)
    budget_status: Mapped[str] = mapped_column(String(24), default="unavailable")
    poster_url: Mapped[str | None] = mapped_column(Text)
    backdrop_url: Mapped[str | None] = mapped_column(Text)
    trailer_url: Mapped[str | None] = mapped_column(Text)
    homepage_url: Mapped[str | None] = mapped_column(Text)
    primary_source: Mapped[str] = mapped_column(String(32))
    source_confidence: Mapped[float] = mapped_column(Float, default=0.5)
    data_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    external_ids: Mapped[list["ExternalIdentifier"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    credits: Mapped[list["Credit"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    companies: Mapped[list["MovieCompany"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    releases: Mapped[list["Release"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    observations: Mapped[list["SourceObservation"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    buzz_snapshots: Mapped[list["BuzzSnapshot"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    actual_grosses: Mapped[list["ActualGross"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )
    forecasts: Mapped[list["ForecastRun"]] = relationship(
        back_populates="movie",
        cascade="all, delete-orphan",
    )


class ExternalIdentifier(Base):
    __tablename__ = "external_identifiers"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_external_identifier_source_value"),
        UniqueConstraint("movie_id", "source", name="uq_external_identifier_movie_source"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str] = mapped_column(String(128), index=True)
    source_url: Mapped[str | None] = mapped_column(Text)

    movie: Mapped[Movie] = relationship(back_populates="external_ids")


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_people_source_id"),
        Index("ix_people_name", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(240))
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(128))
    profile_url: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(Text)

    credits: Mapped[list["Credit"]] = relationship(back_populates="person")


class Credit(Base):
    __tablename__ = "credits"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "person_id",
            "department",
            "job",
            "character_name",
            name="uq_credit_identity",
        ),
        Index("ix_credits_movie_department_order", "movie_id", "department", "billing_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    person_id: Mapped[str] = mapped_column(ForeignKey("people.id", ondelete="CASCADE"))
    department: Mapped[str] = mapped_column(String(48))
    job: Mapped[str] = mapped_column(String(96), default="")
    character_name: Mapped[str] = mapped_column(String(300), default="")
    billing_order: Mapped[int | None] = mapped_column(Integer)

    movie: Mapped[Movie] = relationship(back_populates="credits")
    person: Mapped[Person] = relationship(back_populates="credits")


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_companies_source_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(240), index=True)
    source: Mapped[str] = mapped_column(String(32))
    source_id: Mapped[str] = mapped_column(String(128))
    logo_url: Mapped[str | None] = mapped_column(Text)
    origin_country: Mapped[str | None] = mapped_column(String(8))

    movies: Mapped[list["MovieCompany"]] = relationship(back_populates="company")


class MovieCompany(Base):
    __tablename__ = "movie_companies"
    __table_args__ = (
        UniqueConstraint("movie_id", "company_id", "role", name="uq_movie_company_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(48), default="production")

    movie: Mapped[Movie] = relationship(back_populates="companies")
    company: Mapped[Company] = relationship(back_populates="movies")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "country_code",
            "release_type",
            "release_date",
            name="uq_release_identity",
        ),
        Index("ix_releases_country_date", "country_code", "release_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    country_code: Mapped[str] = mapped_column(String(8))
    release_type: Mapped[str] = mapped_column(String(32))
    release_date: Mapped[date] = mapped_column(Date)
    certification: Mapped[str | None] = mapped_column(String(24))
    note: Mapped[str | None] = mapped_column(Text)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    source_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_observations.id", ondelete="SET NULL"),
    )

    movie: Mapped[Movie] = relationship(back_populates="releases")


class SourceObservation(Base):
    __tablename__ = "source_observations"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "source",
            "observation_type",
            "raw_checksum",
            name="uq_observation_checksum",
        ),
        Index("ix_observations_movie_time", "movie_id", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str | None] = mapped_column(
        ForeignKey("movies.id", ondelete="CASCADE"),
        index=True,
    )
    source: Mapped[str] = mapped_column(String(32), index=True)
    observation_type: Mapped[str] = mapped_column(String(64), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    raw_checksum: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    forecast_eligible: Mapped[bool] = mapped_column(Boolean, default=True)

    movie: Mapped[Movie | None] = relationship(back_populates="observations")


class BuzzSnapshot(Base):
    __tablename__ = "buzz_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "source",
            "metric",
            "observed_at",
            name="uq_buzz_snapshot",
        ),
        Index("ix_buzz_movie_time", "movie_id", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    metric: Mapped[str] = mapped_column(String(64))
    value: Mapped[float] = mapped_column(Float)
    normalized_value: Mapped[float | None] = mapped_column(Float)
    momentum: Mapped[float | None] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_url: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    raw_checksum: Mapped[str] = mapped_column(String(64))

    movie: Mapped[Movie] = relationship(back_populates="buzz_snapshots")


class ActualGross(Base):
    __tablename__ = "actual_grosses"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "target",
            "source",
            "observed_at",
            name="uq_actual_observation",
        ),
        Index("ix_actual_movie_target_time", "movie_id", "target", "observed_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    target: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    amount_status: Mapped[str] = mapped_column(String(24))
    source: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_checksum: Mapped[str] = mapped_column(String(64))
    conflict_group: Mapped[str | None] = mapped_column(String(64))

    movie: Mapped[Movie] = relationship(back_populates="actual_grosses")


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    version: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    model_kind: Mapped[str] = mapped_column(String(48))
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    artifact_checksum: Mapped[str | None] = mapped_column(String(64))
    feature_manifest_json: Mapped[str] = mapped_column(Text)
    metrics_json: Mapped[str] = mapped_column(Text)
    training_cutoff: Mapped[date | None] = mapped_column(Date)
    promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    forecasts: Mapped[list["ForecastRun"]] = relationship(back_populates="model_version")


class ForecastRun(Base):
    __tablename__ = "forecast_runs"
    __table_args__ = (
        UniqueConstraint(
            "movie_id",
            "model_version_id",
            "data_cutoff",
            "horizon_days",
            "forecast_type",
            name="uq_forecast_lock",
        ),
        Index("ix_forecast_movie_cutoff", "movie_id", "data_cutoff"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    model_version_id: Mapped[str] = mapped_column(
        ForeignKey("model_versions.id", ondelete="RESTRICT"),
    )
    data_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    horizon_days: Mapped[int | None] = mapped_column(Integer)
    forecast_type: Mapped[str] = mapped_column(String(32), default="official")
    targets_json: Mapped[str] = mapped_column(Text)
    factors_json: Mapped[str] = mapped_column(Text)
    buzz_json: Mapped[str] = mapped_column(Text)
    comparables_json: Mapped[str] = mapped_column(Text)
    fairness_json: Mapped[str] = mapped_column(Text)
    evidence_manifest_json: Mapped[str] = mapped_column(Text)
    confidence_score: Mapped[float] = mapped_column(Float)
    feature_manifest_hash: Mapped[str] = mapped_column(String(64))
    limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    movie: Mapped[Movie] = relationship(back_populates="forecasts")
    model_version: Mapped[ModelVersion] = relationship(back_populates="forecasts")
    ledger_entry: Mapped["LedgerEntry | None"] = relationship(
        back_populates="forecast",
        cascade="all, delete-orphan",
        uselist=False,
    )


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    sequence: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    forecast_run_id: Mapped[str] = mapped_column(
        ForeignKey("forecast_runs.id", ondelete="CASCADE"),
        unique=True,
    )
    previous_hash: Mapped[str | None] = mapped_column(String(64))
    payload_hash: Mapped[str] = mapped_column(String(64))
    ledger_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    sealed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    forecast: Mapped[ForecastRun] = relationship(back_populates="ledger_entry")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_watchlist_user_movie"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[str] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (Index("ix_job_runs_name_started", "job_name", "started_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    job_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cursor_json: Mapped[str] = mapped_column(Text, default="{}")
    stats_json: Mapped[str] = mapped_column(Text, default="{}")
    error_text: Mapped[str | None] = mapped_column(Text)
