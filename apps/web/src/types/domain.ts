export const GENRES = [
  "Action",
  "Adventure",
  "Animation",
  "Comedy",
  "Crime",
  "Documentary",
  "Drama",
  "Family",
  "Fantasy",
  "History",
  "Horror",
  "Music",
  "Mystery",
  "Romance",
  "Science Fiction",
  "Thriller",
  "War",
  "Western",
] as const;

export type Genre = (typeof GENRES)[number];

export const PREMIUM_FORMATS = [
  "Standard",
  "IMAX",
  "Dolby Cinema",
  "3D",
  "4DX",
] as const;

export type PremiumFormat = (typeof PREMIUM_FORMATS)[number];

export type SourceMaterial =
  | "Original"
  | "Book"
  | "Comic / graphic novel"
  | "Video game"
  | "True story"
  | "Sequel"
  | "Remake"
  | "Toy / brand";

export type AudienceRating = "G" | "PG" | "PG-13" | "R" | "NC-17" | "Not rated";

export interface ForecastRequest {
  title: string;
  synopsis: string;
  genres: Genre[];
  budget: number;
  marketing_budget: number;
  release_date: string;
  runtime_minutes: number;
  audience_rating: AudienceRating;
  director: string | null;
  cast: string[];
  studio: string | null;
  source_material: SourceMaterial;
  franchise_strength: number;
  premium_formats: PremiumFormat[];
  theater_count: number;
  competition_score: number;
  social_buzz: number;
  trailer_engagement: number;
  international_appeal: number;
  production_readiness: number;
}

export interface RevenueRange {
  low: number;
  expected: number;
  high: number;
}

export interface ForecastResponse {
  model_version: string;
  generated_at: string;
  input: ForecastRequest;
  financials: {
    worldwide_gross: RevenueRange;
    domestic_gross: RevenueRange;
    international_gross: RevenueRange;
    opening_weekend: RevenueRange;
    break_even_gross: number;
    expected_profit: number;
    expected_roi: number;
    break_even_probability: number;
    hit_probability: number;
  };
  factors: Array<{
    key: string;
    label: string;
    value: string;
    impact: number;
    direction: "positive" | "negative" | "neutral";
    evidence: string;
    mutable: boolean;
  }>;
  synopsis_signals: Array<{
    label: string;
    score: number;
    detail: string;
  }>;
  robustness: {
    score: number;
    label: "Fragile" | "Mixed" | "Resilient";
    profitable_scenarios: number;
    downside_gross: number;
    upside_gross: number;
    key_risk: string;
  };
  confidence: {
    score: number;
    level: "Low" | "Medium" | "High";
    data_completeness: number;
    calibration_segment: string;
    caveats: string[];
  };
  fairness: {
    protected_attributes_used: boolean;
    audit_status: "pass" | "watch" | "insufficient_data";
    notes: string[];
  };
  methodology_note: string;
}

export interface OptimizeRequest {
  title: string;
  synopsis: string;
  genres: Genre[];
  target_budget: number | null;
  earliest_release: string;
  latest_release: string;
  fixed_director: string | null;
  fixed_cast: string[];
  risk_tolerance: "conservative" | "balanced" | "aggressive";
}

export interface PlanRecommendation {
  id: string;
  label: string;
  thesis: string;
  request: ForecastRequest;
  forecast: ForecastResponse;
  reasons: string[];
}

export interface OptimizeResponse {
  plans: PlanRecommendation[];
  recommendation: string;
  constraint_notes: string[];
}

export interface UpcomingMovie {
  id: string;
  title: string;
  release_date: string;
  synopsis: string;
  genres: string[];
  poster_url: string | null;
  backdrop_url: string | null;
  director: string | null;
  cast: string[];
  studio: string | null;
  data_source: "tmdb" | "research_corpus" | "official_seed";
  forecast_ready: boolean;
}

export type ReleaseStatus =
  | "confirmed"
  | "date_tentative"
  | "year_only"
  | "in_theaters"
  | "released"
  | "gross_closed";

export interface MoneyInterval {
  p10: number;
  p50: number;
  p90: number;
  currency: string;
}

export interface ActualGross {
  target: string;
  amount: number;
  currency: string;
  amount_status: "provisional" | "final" | "conflicted";
  source: string;
  source_url: string;
  observed_at: string;
  confidence: number;
  conflicts: number[];
}

export interface ForecastBadge {
  availability: "locked" | "pending" | "unavailable";
  p10: number | null;
  p50: number | null;
  p90: number | null;
  horizon_days: number | null;
  data_cutoff: string | null;
  model_version: string | null;
  ledger_hash: string | null;
}

export interface MovieSummary {
  id: string;
  slug: string;
  title: string;
  original_title: string | null;
  synopsis: string | null;
  release_status: ReleaseStatus;
  release_date: string | null;
  release_year: number;
  date_precision: "day" | "month" | "year";
  countdown_days: number | null;
  genres: string[];
  runtime_minutes: number | null;
  certification: string | null;
  original_language: string | null;
  origin_country: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
  trailer_url: string | null;
  director: string | null;
  top_cast: string[];
  studio: string | null;
  forecast: ForecastBadge;
  worldwide_actual: ActualGross | null;
  buzz_momentum: number | null;
  data_updated_at: string;
  primary_source: string;
  source_confidence: number;
}

export interface EvidenceRecord {
  source: string;
  observation_type: string;
  observed_at: string;
  source_url: string;
  confidence: number;
  raw_checksum: string;
  forecast_eligible: boolean;
}

export interface MovieDetail extends MovieSummary {
  budget: number | null;
  budget_status:
    "reported" | "range_midpoint" | "model_imputed" | "unavailable";
  homepage_url: string | null;
  external_ids: Array<{
    source: string;
    external_id: string;
    source_url: string | null;
  }>;
  credits: Array<{
    person_id: string;
    name: string;
    department: string;
    job: string;
    character_name: string;
    billing_order: number | null;
    image_url: string | null;
  }>;
  companies: Array<{
    id: string;
    name: string;
    role: string;
    logo_url: string | null;
  }>;
  releases: Array<{
    country_code: string;
    release_type: string;
    release_date: string;
    certification: string | null;
    note: string | null;
    is_confirmed: boolean;
  }>;
  actuals: ActualGross[];
  evidence: EvidenceRecord[];
}

export interface BuzzPoint {
  source: string;
  metric: string;
  value: number;
  normalized_value: number | null;
  momentum: number | null;
  observed_at: string;
  source_url: string;
  confidence: number;
}

export interface MovieForecast {
  film: MovieSummary;
  forecast_type: "official" | "evaluation" | "reconstruction";
  data_cutoff: string;
  horizon_days: number | null;
  model_version: string;
  model_kind: string;
  targets: Record<string, MoneyInterval | null>;
  actuals: Record<string, ActualGross | null>;
  errors: Record<string, number | null>;
  grouped_factors: Array<{
    key: string;
    label: string;
    group: string;
    value: string;
    impact: number | null;
    direction: "positive" | "negative" | "neutral" | "unknown";
    evidence: string;
    source_count: number;
  }>;
  buzz: BuzzPoint[];
  comparables: Array<{
    movie_id: string;
    slug: string;
    title: string;
    release_year: number;
    similarity: number;
    actual_worldwide: number | null;
    reason: string;
  }>;
  fairness: {
    protected_attributes_used: boolean;
    audit_status: "pass" | "watch" | "insufficient_data";
    evaluation_only_attributes: string[];
    cohort_definition: string;
    notes: string[];
  };
  evidence: EvidenceRecord[];
  confidence_score: number;
  feature_manifest_hash: string;
  ledger_hash: string;
  ledger_sequence: number;
  generated_at: string;
  limitations: string[];
}

export interface ForecastHistoryPoint {
  forecast_id: string;
  forecast_type: "official" | "evaluation" | "reconstruction";
  data_cutoff: string;
  horizon_days: number | null;
  worldwide: MoneyInterval | null;
  actual_worldwide: number | null;
  model_version: string;
  ledger_hash: string;
  generated_at: string;
}

export interface MovieListResponse {
  items: MovieSummary[];
  total: number;
  limit: number;
  offset: number;
  data_freshness: string | null;
  attribution: string;
}

export interface BacktestResponse {
  items: Array<{
    movie: MovieSummary;
    forecast: ForecastHistoryPoint;
    actual_worldwide: ActualGross | null;
    absolute_error: number | null;
    absolute_percentage_error: number | null;
  }>;
  metrics: {
    count: number;
    mae: number | null;
    median_absolute_error: number | null;
    log_mae: number | null;
    interval_coverage: number | null;
    interval_target: number;
  };
  cutoff: string | null;
  model_version: string | null;
  methodology_note: string;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
  created_at: string;
}

export interface SavedProject {
  id: string;
  title: string;
  project_type: string;
  payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AdminOverview {
  users: number;
  saved_projects: number;
  active_sessions: number;
  forecast_projects: number;
  optimization_projects: number;
  recent_projects: Array<{
    id: string;
    title: string;
    project_type: string;
    owner_name: string;
    updated_at: string;
  }>;
}
