from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

GENRE_BUCKETS = (
    "Action",
    "Animation",
    "Comedy",
    "Drama",
    "Fantasy",
    "Horror",
    "Other",
    "Romance",
    "SciFi",
    "Thriller",
)

STRUCTURED_FEATURES = (
    "log_budget",
    "decade",
    "director_avg_revenue_log",
    "director_num_films",
    "director_max_revenue_log",
    *(f"genre_{genre}" for genre in GENRE_BUCKETS),
)

FEATURE_NAMES = (
    *STRUCTURED_FEATURES,
    *(f"bert_{index}" for index in range(768)),
)

if len(FEATURE_NAMES) != 783:
    raise RuntimeError("bert-xgb-v1 feature contract must contain exactly 783 values")


@dataclass(frozen=True)
class DirectorHistory:
    films: int
    average_revenue: float
    maximum_revenue: float


def map_genre(genres: Sequence[str]) -> str:
    normalized = {genre.casefold() for genre in genres}
    priority = (
        ("action", "Action"),
        ("animation", "Animation"),
        ("comedy", "Comedy"),
        ("drama", "Drama"),
        ("fantasy", "Fantasy"),
        ("horror", "Horror"),
        ("romance", "Romance"),
        ("science fiction", "SciFi"),
        ("sci-fi", "SciFi"),
        ("thriller", "Thriller"),
    )
    return next((bucket for source, bucket in priority if source in normalized), "Other")


def structured_vector(
    *,
    budget: float,
    release_year: int,
    director_history: DirectorHistory | None,
    genres: Sequence[str],
) -> np.ndarray:
    history = director_history or DirectorHistory(
        films=0,
        average_revenue=50_000_000.0,
        maximum_revenue=0.0,
    )
    genre = map_genre(genres)
    values = [
        math.log1p(max(0.0, budget)),
        float((release_year // 10) * 10),
        math.log1p(max(0.0, history.average_revenue)),
        float(history.films),
        math.log1p(max(0.0, history.maximum_revenue)),
        *(1.0 if item == genre else 0.0 for item in GENRE_BUCKETS),
    ]
    return np.asarray(values, dtype=np.float32)


def full_feature_vector(
    structured: np.ndarray,
    embedding: np.ndarray,
) -> np.ndarray:
    structured = np.asarray(structured, dtype=np.float32).reshape(-1)
    embedding = np.asarray(embedding, dtype=np.float32).reshape(-1)
    if structured.shape != (15,):
        raise ValueError(f"Expected 15 structured features, got {structured.shape}")
    if embedding.shape != (768,):
        raise ValueError(f"Expected a 768-dimensional BERT embedding, got {embedding.shape}")
    return np.concatenate([structured, embedding]).reshape(1, 783)


def director_history_from_mapping(
    value: Mapping[str, object] | None,
) -> DirectorHistory | None:
    if value is None:
        return None

    def number(key: str, fallback: float = 0.0) -> float:
        candidate = value.get(key, fallback)
        return float(candidate) if isinstance(candidate, (int, float)) else fallback

    average = number("avg_revenue", 50_000_000.0)
    maximum = number("max_revenue", average)
    return DirectorHistory(
        films=int(number("films")),
        average_revenue=average,
        maximum_revenue=maximum,
    )
