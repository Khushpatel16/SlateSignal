from datetime import date

import pytest

from slatesignal.domain.schemas import (
    ForecastRequest,
    Genre,
    PremiumFormat,
    SourceMaterial,
)
from slatesignal.services.forecast import ForecastEngine


@pytest.fixture
def forecast_request() -> ForecastRequest:
    return ForecastRequest(
        title="Glass Horizon",
        synopsis=(
            "A climate cartographer discovers an impossible coastline moving toward the world's "
            "largest cities and must decode its origin before the next tide redraws civilization."
        ),
        genres=[Genre.SCIENCE_FICTION, Genre.THRILLER],
        budget=85_000_000,
        marketing_budget=42_000_000,
        release_date=date(2027, 5, 21),
        runtime_minutes=118,
        director="Denis Villeneuve",
        cast=["Rebecca Ferguson", "John David Washington"],
        studio="Warner Bros.",
        source_material=SourceMaterial.ORIGINAL,
        franchise_strength=15,
        premium_formats=[
            PremiumFormat.STANDARD,
            PremiumFormat.IMAX,
            PremiumFormat.DOLBY,
        ],
        theater_count=3600,
        competition_score=38,
        social_buzz=52,
        trailer_engagement=47,
        international_appeal=74,
        production_readiness=76,
    )


def test_forecast_has_ordered_ranges_and_twenty_factors(
    forecast_request: ForecastRequest,
) -> None:
    result = ForecastEngine().predict(forecast_request)

    worldwide = result.financials.worldwide_gross
    assert worldwide.low < worldwide.expected < worldwide.high
    assert len(result.factors) == 20
    assert 0 <= result.financials.break_even_probability <= 1
    assert 0 <= result.robustness.profitable_scenarios <= 1
    assert result.fairness.protected_attributes_used is False


def test_counterfactual_competition_changes_forecast(
    forecast_request: ForecastRequest,
) -> None:
    engine = ForecastEngine()
    quiet_window = engine.predict(forecast_request.model_copy(update={"competition_score": 15}))
    crowded_window = engine.predict(forecast_request.model_copy(update={"competition_score": 90}))

    assert (
        quiet_window.financials.worldwide_gross.expected
        > crowded_window.financials.worldwide_gross.expected
    )


def test_bigger_budget_changes_scale_but_not_factor_count(
    forecast_request: ForecastRequest,
) -> None:
    engine = ForecastEngine()
    smaller = engine.predict(forecast_request.model_copy(update={"budget": 25_000_000}))
    larger = engine.predict(forecast_request.model_copy(update={"budget": 180_000_000}))

    assert larger.financials.worldwide_gross.expected > smaller.financials.worldwide_gross.expected
    assert len(larger.factors) == len(smaller.factors)


def test_robustness_simulation_is_deterministic(
    forecast_request: ForecastRequest,
) -> None:
    engine = ForecastEngine()
    first = engine.predict(forecast_request)
    second = engine.predict(forecast_request)

    assert first.robustness == second.robustness
