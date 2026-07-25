from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Genre(StrEnum):
    ACTION = "Action"
    ADVENTURE = "Adventure"
    ANIMATION = "Animation"
    COMEDY = "Comedy"
    CRIME = "Crime"
    DOCUMENTARY = "Documentary"
    DRAMA = "Drama"
    FAMILY = "Family"
    FANTASY = "Fantasy"
    HISTORY = "History"
    HORROR = "Horror"
    MUSIC = "Music"
    MYSTERY = "Mystery"
    ROMANCE = "Romance"
    SCIENCE_FICTION = "Science Fiction"
    THRILLER = "Thriller"
    WAR = "War"
    WESTERN = "Western"


class SourceMaterial(StrEnum):
    ORIGINAL = "Original"
    BOOK = "Book"
    COMIC = "Comic / graphic novel"
    GAME = "Video game"
    TRUE_STORY = "True story"
    SEQUEL = "Sequel"
    REMAKE = "Remake"
    TOY = "Toy / brand"


class PremiumFormat(StrEnum):
    STANDARD = "Standard"
    IMAX = "IMAX"
    DOLBY = "Dolby Cinema"
    THREE_D = "3D"
    FOUR_DX = "4DX"


class AudienceRating(StrEnum):
    G = "G"
    PG = "PG"
    PG13 = "PG-13"
    R = "R"
    NC17 = "NC-17"
    NOT_RATED = "Not rated"


class ForecastRequest(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=160)] = "Untitled project"
    synopsis: Annotated[str, Field(min_length=40, max_length=5000)]
    genres: Annotated[list[Genre], Field(min_length=1, max_length=4)]
    budget: Annotated[float, Field(ge=100_000, le=500_000_000)]
    marketing_budget: Annotated[float, Field(ge=0, le=400_000_000)] = 25_000_000
    release_date: date
    runtime_minutes: Annotated[int, Field(ge=55, le=240)] = 110
    audience_rating: AudienceRating = AudienceRating.PG13
    director: Annotated[str | None, Field(max_length=120)] = None
    cast: list[str] = Field(default_factory=list, max_length=8)
    studio: Annotated[str | None, Field(max_length=160)] = None
    source_material: SourceMaterial = SourceMaterial.ORIGINAL
    franchise_strength: Annotated[int, Field(ge=0, le=100)] = 0
    premium_formats: list[PremiumFormat] = Field(
        default_factory=lambda: [PremiumFormat.STANDARD],
        min_length=1,
        max_length=5,
    )
    theater_count: Annotated[int, Field(ge=10, le=6000)] = 2800
    competition_score: Annotated[int, Field(ge=0, le=100)] = 45
    social_buzz: Annotated[int, Field(ge=0, le=100)] = 40
    trailer_engagement: Annotated[int, Field(ge=0, le=100)] = 35
    international_appeal: Annotated[int, Field(ge=0, le=100)] = 55
    production_readiness: Annotated[int, Field(ge=0, le=100)] = 65

    @field_validator("genres")
    @classmethod
    def unique_genres(cls, genres: list[Genre]) -> list[Genre]:
        return list(dict.fromkeys(genres))

    @field_validator("cast")
    @classmethod
    def unique_cast(cls, cast: list[str]) -> list[str]:
        cleaned = [name.strip() for name in cast if name.strip()]
        return list(dict.fromkeys(cleaned))

    @field_validator("premium_formats")
    @classmethod
    def unique_formats(cls, formats: list[PremiumFormat]) -> list[PremiumFormat]:
        return list(dict.fromkeys(formats))


class RevenueRange(BaseModel):
    low: float
    expected: float
    high: float


class FinancialOutcome(BaseModel):
    worldwide_gross: RevenueRange
    domestic_gross: RevenueRange
    international_gross: RevenueRange
    opening_weekend: RevenueRange
    break_even_gross: float
    expected_profit: float
    expected_roi: float
    break_even_probability: float
    hit_probability: float


class FactorContribution(BaseModel):
    key: str
    label: str
    value: str
    impact: float
    direction: Literal["positive", "negative", "neutral"]
    evidence: str
    mutable: bool = True


class SynopsisSignal(BaseModel):
    label: str
    score: int
    detail: str


class RobustnessResult(BaseModel):
    score: int
    label: Literal["Fragile", "Mixed", "Resilient"]
    profitable_scenarios: float
    downside_gross: float
    upside_gross: float
    key_risk: str


class ConfidenceResult(BaseModel):
    score: int
    level: Literal["Low", "Medium", "High"]
    data_completeness: float
    calibration_segment: str
    caveats: list[str]


class FairnessResult(BaseModel):
    protected_attributes_used: bool = False
    audit_status: Literal["pass", "watch", "insufficient_data"]
    notes: list[str]


class ForecastResponse(BaseModel):
    model_version: str
    generated_at: datetime
    input: ForecastRequest
    financials: FinancialOutcome
    factors: list[FactorContribution]
    synopsis_signals: list[SynopsisSignal]
    robustness: RobustnessResult
    confidence: ConfidenceResult
    fairness: FairnessResult
    methodology_note: str


class OptimizeRequest(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=160)] = "Untitled project"
    synopsis: Annotated[str, Field(min_length=80, max_length=5000)]
    genres: Annotated[list[Genre], Field(min_length=1, max_length=4)]
    target_budget: Annotated[float, Field(ge=100_000, le=500_000_000)] | None = None
    earliest_release: date
    latest_release: date
    fixed_director: Annotated[str | None, Field(max_length=120)] = None
    fixed_cast: list[str] = Field(default_factory=list, max_length=4)
    risk_tolerance: Literal["conservative", "balanced", "aggressive"] = "balanced"

    @field_validator("latest_release")
    @classmethod
    def release_window_is_valid(cls, latest: date, info: object) -> date:
        values = getattr(info, "data", {})
        earliest = values.get("earliest_release")
        if earliest and latest < earliest:
            raise ValueError("latest_release must be on or after earliest_release")
        return latest


class PlanRecommendation(BaseModel):
    id: str
    label: str
    thesis: str
    request: ForecastRequest
    forecast: ForecastResponse
    reasons: list[str]


class OptimizeResponse(BaseModel):
    plans: list[PlanRecommendation]
    recommendation: str
    constraint_notes: list[str]


class PersonOption(BaseModel):
    name: str
    role: Literal["director", "cast"]
    films: int
    avg_revenue: float
    hit_rate: float
    genre_fit: float


class StudioOption(BaseModel):
    name: str
    films: int
    avg_revenue: float
    hit_rate: float
    genre_fit: float


class CatalogSearchResponse(BaseModel):
    people: list[PersonOption]
    studios: list[StudioOption]


class UpcomingMovie(BaseModel):
    id: str
    title: str
    release_date: date
    synopsis: str
    genres: list[str]
    poster_url: str | None = None
    backdrop_url: str | None = None
    director: str | None = None
    cast: list[str] = Field(default_factory=list)
    studio: str | None = None
    data_source: Literal["tmdb", "research_corpus", "official_seed"]
    forecast_ready: bool = False


class ReleaseStatus(StrEnum):
    CONFIRMED = "confirmed"
    DATE_TENTATIVE = "date_tentative"
    YEAR_ONLY = "year_only"
    IN_THEATERS = "in_theaters"
    RELEASED = "released"
    GROSS_CLOSED = "gross_closed"


class ForecastAvailability(StrEnum):
    LOCKED = "locked"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class MoneyInterval(BaseModel):
    p10: float
    p50: float
    p90: float
    currency: str = "USD"


class ForecastBadge(BaseModel):
    availability: ForecastAvailability
    p10: float | None = None
    p50: float | None = None
    p90: float | None = None
    horizon_days: int | None = None
    data_cutoff: datetime | None = None
    model_version: str | None = None
    ledger_hash: str | None = None


class ActualGrossPublic(BaseModel):
    target: str
    amount: float
    currency: str
    amount_status: Literal["provisional", "final", "conflicted"]
    source: str
    source_url: str
    observed_at: datetime
    confidence: float
    conflicts: list[float] = Field(default_factory=list)


class MovieSummary(BaseModel):
    id: str
    slug: str
    title: str
    original_title: str | None = None
    synopsis: str | None = None
    release_status: ReleaseStatus
    release_date: date | None = None
    release_year: int
    date_precision: Literal["day", "month", "year"]
    countdown_days: int | None = None
    genres: list[str]
    runtime_minutes: int | None = None
    certification: str | None = None
    original_language: str | None = None
    origin_country: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    trailer_url: str | None = None
    director: str | None = None
    top_cast: list[str] = Field(default_factory=list)
    studio: str | None = None
    forecast: ForecastBadge
    worldwide_actual: ActualGrossPublic | None = None
    buzz_momentum: float | None = None
    data_updated_at: datetime
    primary_source: str
    source_confidence: float


class ExternalIdPublic(BaseModel):
    source: str
    external_id: str
    source_url: str | None = None


class CreditPublic(BaseModel):
    person_id: str
    name: str
    department: str
    job: str
    character_name: str
    billing_order: int | None = None
    image_url: str | None = None


class CompanyPublic(BaseModel):
    id: str
    name: str
    role: str
    logo_url: str | None = None


class ReleasePublic(BaseModel):
    country_code: str
    release_type: str
    release_date: date
    certification: str | None = None
    note: str | None = None
    is_confirmed: bool


class EvidenceRecord(BaseModel):
    source: str
    observation_type: str
    observed_at: datetime
    source_url: str
    confidence: float
    raw_checksum: str
    forecast_eligible: bool


class MovieDetail(MovieSummary):
    budget: float | None = None
    budget_status: Literal["reported", "range_midpoint", "model_imputed", "unavailable"]
    homepage_url: str | None = None
    external_ids: list[ExternalIdPublic]
    credits: list[CreditPublic]
    companies: list[CompanyPublic]
    releases: list[ReleasePublic]
    actuals: list[ActualGrossPublic]
    evidence: list[EvidenceRecord]


class ForecastFactor(BaseModel):
    key: str
    label: str
    group: str
    value: str
    impact: float | None = None
    direction: Literal["positive", "negative", "neutral", "unknown"]
    evidence: str
    source_count: int = 0


class BuzzPoint(BaseModel):
    source: str
    metric: str
    value: float
    normalized_value: float | None = None
    momentum: float | None = None
    observed_at: datetime
    source_url: str
    confidence: float


class ComparableFilm(BaseModel):
    movie_id: str
    slug: str
    title: str
    release_year: int
    similarity: float
    actual_worldwide: float | None = None
    reason: str


class ForecastFairness(BaseModel):
    protected_attributes_used: bool = False
    audit_status: Literal["pass", "watch", "insufficient_data"]
    evaluation_only_attributes: list[str] = Field(default_factory=list)
    cohort_definition: str
    notes: list[str]


class MovieForecast(BaseModel):
    film: MovieSummary
    forecast_type: Literal["official", "evaluation", "reconstruction"]
    data_cutoff: datetime
    horizon_days: int | None
    model_version: str
    model_kind: str
    targets: dict[str, MoneyInterval | None]
    actuals: dict[str, ActualGrossPublic | None]
    errors: dict[str, float | None]
    grouped_factors: list[ForecastFactor]
    buzz: list[BuzzPoint]
    comparables: list[ComparableFilm]
    fairness: ForecastFairness
    evidence: list[EvidenceRecord]
    confidence_score: float
    feature_manifest_hash: str
    ledger_hash: str
    ledger_sequence: int
    generated_at: datetime
    limitations: list[str]


class ForecastHistoryPoint(BaseModel):
    forecast_id: str
    forecast_type: Literal["official", "evaluation", "reconstruction"]
    data_cutoff: datetime
    horizon_days: int | None
    worldwide: MoneyInterval | None
    actual_worldwide: float | None = None
    model_version: str
    ledger_hash: str
    generated_at: datetime


class MovieListResponse(BaseModel):
    items: list[MovieSummary]
    total: int
    limit: int
    offset: int
    data_freshness: datetime | None = None
    attribution: str = "This product uses the TMDB API but is not endorsed or certified by TMDB."


class BacktestRecord(BaseModel):
    movie: MovieSummary
    forecast: ForecastHistoryPoint
    actual_worldwide: ActualGrossPublic | None
    absolute_error: float | None
    absolute_percentage_error: float | None


class BacktestMetrics(BaseModel):
    count: int
    mae: float | None
    median_absolute_error: float | None
    log_mae: float | None
    interval_coverage: float | None
    interval_target: float = 0.8


class BacktestResponse(BaseModel):
    items: list[BacktestRecord]
    metrics: BacktestMetrics
    cutoff: datetime | None
    model_version: str | None
    methodology_note: str


class UserCreate(BaseModel):
    email: EmailStr
    display_name: Annotated[str, Field(min_length=2, max_length=80)]
    password: Annotated[str, Field(min_length=10, max_length=128)]


class UserLogin(BaseModel):
    email: EmailStr
    password: Annotated[str, Field(min_length=1, max_length=128)]


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    display_name: str
    role: Literal["user", "admin"]
    created_at: datetime


class SavedProjectCreate(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=160)]
    project_type: Literal["scenario", "forecast", "optimization"] = "scenario"
    payload: dict[str, object]


class SavedProjectPublic(BaseModel):
    id: str
    title: str
    project_type: str
    payload: dict[str, object]
    created_at: datetime
    updated_at: datetime


class AdminRecentProject(BaseModel):
    id: str
    title: str
    project_type: str
    owner_name: str
    updated_at: datetime


class AdminOverview(BaseModel):
    users: int
    saved_projects: int
    active_sessions: int
    forecast_projects: int
    optimization_projects: int
    recent_projects: list[AdminRecentProject]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    model_mode: Literal["decision_engine", "artifact"]
    database: str
    knowledge_base_loaded: bool
    tmdb_configured: bool
