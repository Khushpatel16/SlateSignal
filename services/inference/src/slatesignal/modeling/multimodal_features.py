from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

import numpy as np

from slatesignal.modeling.features import GENRE_BUCKETS, map_genre

CERTIFICATION_BUCKETS = ("G", "PG", "PG-13", "R", "OTHER")

MULTIMODAL_STRUCTURED_FEATURES = (
    "log_budget_real_2025",
    "budget_missing",
    "release_year_centered",
    "director_avg_revenue_log",
    "director_num_films",
    "director_max_revenue_log",
    "director_missing",
    "cast_avg_revenue_log",
    "cast_num_films",
    "cast_max_revenue_log",
    "cast_missing",
    "studio_avg_revenue_log",
    "studio_num_films",
    "studio_max_revenue_log",
    "studio_missing",
    "release_month_sin",
    "release_month_cos",
    "release_month_missing",
    "holiday_window",
    "nearby_competition",
    "competition_missing",
    "runtime_scaled",
    "runtime_missing",
    "franchise_ip",
    "sequel_number",
    *(f"certification_{item}" for item in CERTIFICATION_BUCKETS),
    "certification_missing",
    *(f"genre_{item}" for item in GENRE_BUCKETS),
    "distribution_scale",
    "distribution_scale_missing",
    "premium_format_count",
    "premium_formats_missing",
    "english_language",
    "language_missing",
    "producer_writer_history",
    "producer_writer_missing",
    "google_momentum",
    "google_missing",
    "wikipedia_attention",
    "wikipedia_missing",
    "trailer_momentum",
    "trailer_missing",
    "news_reddit_attention",
    "news_reddit_missing",
)

MULTIMODAL_FEATURE_NAMES = (
    *MULTIMODAL_STRUCTURED_FEATURES,
    *(f"bert_{index}" for index in range(768)),
)


@dataclass(frozen=True)
class TrackRecord:
    films: int = 0
    average_revenue: float = 50_000_000.0
    maximum_revenue: float = 0.0
    missing: bool = True


@dataclass(frozen=True)
class MultimodalInput:
    title: str
    budget_real_2025: float
    budget_missing: bool
    release_year: int
    release_date: date | None
    director: TrackRecord
    cast: TrackRecord
    studio: TrackRecord
    genres: Sequence[str]
    runtime_minutes: int | None
    certification: str | None
    nearby_competition: float | None = None
    distribution_scale: float | None = None
    premium_format_count: float | None = None
    original_language: str | None = None
    producer_writer_history: float | None = None
    google_momentum: float | None = None
    wikipedia_attention: float | None = None
    trailer_momentum: float | None = None
    news_reddit_attention: float | None = None


def structured_multimodal_vector(item: MultimodalInput) -> np.ndarray:
    month = item.release_date.month if item.release_date else None
    angle = 2 * math.pi * (month - 1) / 12 if month else 0.0
    certification = _certification(item.certification)
    genre = map_genre(item.genres)
    franchise, sequel_number = franchise_signals(item.title)
    values = [
        math.log1p(max(0.0, item.budget_real_2025)),
        float(item.budget_missing),
        float(item.release_year - 2000),
        math.log1p(max(0.0, item.director.average_revenue)),
        float(item.director.films),
        math.log1p(max(0.0, item.director.maximum_revenue)),
        float(item.director.missing),
        math.log1p(max(0.0, item.cast.average_revenue)),
        float(item.cast.films),
        math.log1p(max(0.0, item.cast.maximum_revenue)),
        float(item.cast.missing),
        math.log1p(max(0.0, item.studio.average_revenue)),
        float(item.studio.films),
        math.log1p(max(0.0, item.studio.maximum_revenue)),
        float(item.studio.missing),
        math.sin(angle),
        math.cos(angle),
        float(month is None),
        float(month in {5, 6, 7, 11, 12} if month else False),
        float(item.nearby_competition or 0.0),
        float(item.nearby_competition is None),
        float(item.runtime_minutes or 0) / 120.0,
        float(item.runtime_minutes is None),
        franchise,
        sequel_number,
        *(1.0 if candidate == certification else 0.0 for candidate in CERTIFICATION_BUCKETS),
        float(item.certification is None),
        *(1.0 if candidate == genre else 0.0 for candidate in GENRE_BUCKETS),
        float(item.distribution_scale or 0.0),
        float(item.distribution_scale is None),
        float(item.premium_format_count or 0.0),
        float(item.premium_format_count is None),
        float((item.original_language or "").casefold() == "en"),
        float(item.original_language is None),
        float(item.producer_writer_history or 0.0),
        float(item.producer_writer_history is None),
        float(item.google_momentum or 0.0),
        float(item.google_momentum is None),
        float(item.wikipedia_attention or 0.0),
        float(item.wikipedia_attention is None),
        float(item.trailer_momentum or 0.0),
        float(item.trailer_momentum is None),
        float(item.news_reddit_attention or 0.0),
        float(item.news_reddit_attention is None),
    ]
    output = np.asarray(values, dtype=np.float32)
    expected = len(MULTIMODAL_STRUCTURED_FEATURES)
    if output.shape != (expected,):
        raise ValueError(f"Expected {expected} structured values, got {output.shape}")
    return output


def full_multimodal_vector(
    structured: np.ndarray,
    embedding: np.ndarray,
) -> np.ndarray:
    structured = np.asarray(structured, dtype=np.float32).reshape(-1)
    embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if structured.shape != (len(MULTIMODAL_STRUCTURED_FEATURES),):
        raise ValueError("Corrected structured feature shape does not match its manifest")
    if embedding.shape != (768,):
        raise ValueError("BERT embedding must contain 768 values")
    return np.concatenate([structured, embedding])


def track_record(value: Mapping[str, object] | None) -> TrackRecord:
    if value is None:
        return TrackRecord()

    def number(key: str, fallback: float) -> float:
        candidate = value.get(key)
        return float(candidate) if isinstance(candidate, (int, float)) else fallback

    average = number("avg_revenue", 50_000_000.0)
    return TrackRecord(
        films=int(number("films", 0)),
        average_revenue=average,
        maximum_revenue=number("max_revenue", average),
        missing=False,
    )


def franchise_signals(title: str) -> tuple[float, float]:
    normalized = title.casefold()
    sequel_terms = (
        "part ",
        "chapter ",
        "returns",
        "forever",
        "legacy",
        "resurrection",
        "rise of",
    )
    number_match = re.search(r"(?:\s|:)(\d{1,2})(?:\s|$)", normalized)
    roman_match = re.search(r"\b(ii|iii|iv|v|vi|vii|viii|ix|x)\b", normalized)
    number = float(number_match.group(1)) if number_match else 0.0
    if roman_match:
        number = float(
            {
                "ii": 2,
                "iii": 3,
                "iv": 4,
                "v": 5,
                "vi": 6,
                "vii": 7,
                "viii": 8,
                "ix": 9,
                "x": 10,
            }[roman_match.group(1)]
        )
    franchise = float(
        number > 1 or roman_match is not None or any(term in normalized for term in sequel_terms)
    )
    return franchise, number


def _certification(value: str | None) -> str:
    if not value:
        return "OTHER"
    normalized = value.upper().replace("_", "-").strip()
    return normalized if normalized in CERTIFICATION_BUCKETS else "OTHER"
