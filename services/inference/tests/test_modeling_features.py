from datetime import date
from pathlib import Path

import numpy as np
import pytest

from slatesignal.modeling.features import (
    DirectorHistory,
    director_history_from_mapping,
    full_feature_vector,
    map_genre,
    structured_vector,
)
from slatesignal.modeling.inflation import (
    annual_cpi,
    cpi_for_year,
    from_base_year_dollars,
    to_base_year_dollars,
)
from slatesignal.modeling.multimodal_features import (
    MULTIMODAL_FEATURE_NAMES,
    MULTIMODAL_STRUCTURED_FEATURES,
    MultimodalInput,
    TrackRecord,
    franchise_signals,
    full_multimodal_vector,
    structured_multimodal_vector,
    track_record,
)


def test_inflation_normalization_round_trips_and_projects(tmp_path: Path) -> None:
    source = tmp_path / "cpi.csv"
    source.write_text(
        "DATE,CPIAUCSL\n2024-01-01,300\n2024-02-01,302\n2025-01-01,310\n2025-02-01,312\n.\n",
        encoding="utf-8",
    )
    annual_cpi.cache_clear()
    values = annual_cpi(source)

    real = to_base_year_dollars(100, year=2024, values=values)
    assert real == pytest.approx(100 * 311 / 301)
    assert from_base_year_dollars(real, year=2024, values=values) == pytest.approx(100)
    assert cpi_for_year(values, 2026) == pytest.approx(311 * 1.024)
    assert cpi_for_year(values, 1970) == 301


def test_original_feature_contract_is_exact_and_shape_checked() -> None:
    history = director_history_from_mapping(
        {"films": 4, "avg_revenue": 80_000_000, "max_revenue": 240_000_000}
    )
    assert history == DirectorHistory(4, 80_000_000, 240_000_000)
    assert map_genre(["Adventure", "Science Fiction"]) == "SciFi"
    structured = structured_vector(
        budget=60_000_000,
        release_year=2027,
        director_history=history,
        genres=["Science Fiction"],
    )
    vector = full_feature_vector(structured, np.zeros(768, dtype=np.float32))

    assert structured.shape == (15,)
    assert vector.shape == (1, 783)
    with pytest.raises(ValueError):
        full_feature_vector(structured[:-1], np.zeros(768))
    with pytest.raises(ValueError):
        full_feature_vector(structured, np.zeros(767))


def test_corrected_multimodal_contract_encodes_known_and_missing_fields() -> None:
    item = MultimodalInput(
        title="Example Film III",
        budget_real_2025=120_000_000,
        budget_missing=False,
        release_year=2027,
        release_date=date(2027, 12, 17),
        director=TrackRecord(5, 160_000_000, 500_000_000, False),
        cast=TrackRecord(12, 90_000_000, 700_000_000, False),
        studio=TrackRecord(20, 130_000_000, 1_000_000_000, False),
        genres=["Action"],
        runtime_minutes=142,
        certification="PG_13",
        nearby_competition=3,
        distribution_scale=4200,
        premium_format_count=3,
        original_language="en",
        producer_writer_history=0.7,
        google_momentum=0.4,
        wikipedia_attention=0.6,
        trailer_momentum=0.8,
        news_reddit_attention=0.5,
    )
    structured = structured_multimodal_vector(item)
    full = full_multimodal_vector(
        structured,
        np.ones(768, dtype=np.float32),
    )

    assert structured.shape == (len(MULTIMODAL_STRUCTURED_FEATURES),)
    assert full.shape == (len(MULTIMODAL_FEATURE_NAMES),)
    assert franchise_signals("Example Film III") == (1.0, 3.0)
    assert franchise_signals("Example Film: 4") == (1.0, 4.0)
    assert franchise_signals("Example Film Returns") == (1.0, 0.0)
    assert franchise_signals("Example Film") == (0.0, 0.0)


def test_track_record_and_multimodal_shape_guards() -> None:
    assert track_record(None).missing is True
    record = track_record({"films": 3, "avg_revenue": 7, "max_revenue": 11})
    assert record == TrackRecord(3, 7, 11, False)
    with pytest.raises(ValueError):
        full_multimodal_vector(np.zeros(1), np.zeros(768))
    with pytest.raises(ValueError):
        full_multimodal_vector(
            np.zeros(len(MULTIMODAL_STRUCTURED_FEATURES)),
            np.zeros(1),
        )
