from __future__ import annotations

import hashlib
import math
import random
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from statistics import NormalDist
from typing import Any, Literal

from slatesignal.domain.schemas import (
    ConfidenceResult,
    FactorContribution,
    FairnessResult,
    FinancialOutcome,
    ForecastRequest,
    ForecastResponse,
    Genre,
    PremiumFormat,
    RevenueRange,
    RobustnessResult,
    SourceMaterial,
    SynopsisSignal,
)
from slatesignal.services.knowledge import KnowledgeBase, get_knowledge_base

MODEL_VERSION = "decision-engine-2026.07"
Z_80 = 1.2815515655446004


@dataclass(frozen=True)
class RawFactor:
    key: str
    label: str
    value: str
    log_impact: float
    evidence: str
    mutable: bool = True


class ForecastEngine:
    def __init__(self, knowledge: KnowledgeBase | None = None) -> None:
        self.knowledge = knowledge or get_knowledge_base()

    def predict(self, request: ForecastRequest) -> ForecastResponse:
        synopsis_signals = self._synopsis_signals(request.synopsis)
        factors = self._factor_impacts(request, synopsis_signals)
        global_stats = self.knowledge.global_stats
        median_budget = float(global_stats["median_budget"])
        median_revenue = float(global_stats["median_revenue"])

        log_revenue = math.log(median_revenue)
        log_revenue += 0.74 * math.log(request.budget / median_budget)
        log_revenue += sum(factor.log_impact for factor in factors)
        expected = max(50_000.0, min(3_500_000_000.0, math.exp(log_revenue)))

        sigma = self._uncertainty(request)
        low = expected * math.exp(-Z_80 * sigma)
        high = expected * math.exp(Z_80 * sigma)
        international_share = max(0.30, min(0.78, 0.43 + request.international_appeal * 0.003))
        domestic_share = 1 - international_share
        opening_share = self._opening_share(request)
        financials = self._financials(
            request=request,
            low=low,
            expected=expected,
            high=high,
            domestic_share=domestic_share,
            opening_share=opening_share,
            sigma=sigma,
        )
        factor_output = self._factor_contributions(factors, expected)
        confidence = self._confidence(request, sigma)
        robustness = self._robustness(request, expected, sigma, factor_output)

        return ForecastResponse(
            model_version=MODEL_VERSION,
            generated_at=datetime.now(UTC),
            input=request,
            financials=financials,
            factors=factor_output,
            synopsis_signals=synopsis_signals,
            robustness=robustness,
            confidence=confidence,
            fairness=FairnessResult(
                protected_attributes_used=False,
                audit_status="watch",
                notes=[
                    "Protected demographic attributes are excluded from revenue scoring.",
                    (
                        "Historical opportunity is not evenly distributed, so track-record "
                        "features can carry proxy bias."
                    ),
                    (
                        "Recommendation exposure should be audited before production use; "
                        "the current source has limited representation coverage."
                    ),
                ],
            ),
            methodology_note=(
                "An 80% calibrated scenario range from historical budget, genre, release, talent, "
                "distribution, demand, and synopsis signals. This is decision support, not a "
                "guarantee."
            ),
        )

    def _factor_impacts(
        self,
        request: ForecastRequest,
        synopsis_signals: list[SynopsisSignal],
    ) -> list[RawFactor]:
        factors: list[RawFactor] = []
        global_stats = self.knowledge.global_stats
        global_roi = float(global_stats["median_revenue"]) / float(global_stats["median_budget"])

        factors.append(
            RawFactor(
                key="budget",
                label="Production budget",
                value=_money(request.budget),
                log_impact=0.0,
                evidence=(
                    "Budget is the forecast anchor; its elasticity is applied before factor "
                    "attribution."
                ),
            )
        )

        marketing_ratio = request.marketing_budget / request.budget
        marketing_impact = _clamp(0.22 * math.log((marketing_ratio + 0.12) / 0.62), -0.24, 0.22)
        factors.append(
            RawFactor(
                key="marketing",
                label="Marketing support",
                value=f"{marketing_ratio:.0%} of production",
                log_impact=marketing_impact,
                evidence="Diminishing-return lift relative to a 50% production-spend benchmark.",
            )
        )

        genre_impacts: list[float] = []
        for genre in request.genres:
            stats = self.knowledge.genres.get(str(genre))
            if stats:
                genre_roi = stats["median_revenue"] / max(1, stats["median_budget"])
                genre_impacts.append(_clamp(math.log(genre_roi / global_roi), -0.5, 0.5))
        genre_impact = (sum(genre_impacts) / len(genre_impacts) * 0.24) if genre_impacts else 0
        factors.append(
            RawFactor(
                key="genres",
                label="Genre-market fit",
                value=" + ".join(map(str, request.genres)),
                log_impact=genre_impact,
                evidence="Budget-normalized historical returns across the selected genre mix.",
            )
        )

        synopsis_score = sum(signal.score for signal in synopsis_signals) / len(synopsis_signals)
        synopsis_impact = _clamp((synopsis_score - 55) / 100 * 0.34, -0.18, 0.18)
        factors.append(
            RawFactor(
                key="synopsis",
                label="Narrative signals",
                value=f"{synopsis_score:.0f}/100",
                log_impact=synopsis_impact,
                evidence=(
                    "Hook, clarity, stakes, specificity, and global-portability signals in "
                    "the synopsis."
                ),
            )
        )

        director_stats = self.knowledge.director(request.director)
        factors.append(
            self._talent_factor(
                key="director",
                label="Director track record",
                name=request.director,
                stats=director_stats,
                weight=0.26,
            )
        )

        cast_stats: list[dict[str, Any]] = []
        for name in request.cast[:4]:
            stats = self.knowledge.actor(name)
            if stats is not None:
                cast_stats.append(stats)
        if cast_stats:
            cast_performance = sum(self._track_record(stats) for stats in cast_stats) / len(
                cast_stats
            )
            cast_impact = _clamp(cast_performance * 0.16, -0.18, 0.24)
            cast_evidence = (
                f"{len(cast_stats)} of {len(request.cast[:4])} top-billed cast members matched "
                "to prior theatrical history."
            )
        else:
            cast_impact = -0.035 if request.cast else -0.06
            cast_evidence = (
                "No reliable top-billed cast history was available in the current knowledge base."
            )
        factors.append(
            RawFactor(
                key="cast",
                label="Cast bankability",
                value=", ".join(request.cast[:3]) if request.cast else "Unattached",
                log_impact=cast_impact,
                evidence=cast_evidence,
            )
        )

        studio_stats = self.knowledge.studio(request.studio)
        factors.append(
            self._talent_factor(
                key="studio",
                label="Studio execution",
                name=request.studio,
                stats=studio_stats,
                weight=0.19,
            )
        )

        source_impacts = {
            SourceMaterial.ORIGINAL: -0.02,
            SourceMaterial.BOOK: 0.025,
            SourceMaterial.COMIC: 0.07,
            SourceMaterial.GAME: 0.035,
            SourceMaterial.TRUE_STORY: 0.01,
            SourceMaterial.SEQUEL: 0.105,
            SourceMaterial.REMAKE: -0.015,
            SourceMaterial.TOY: 0.06,
        }
        factors.append(
            RawFactor(
                key="source_material",
                label="Source material",
                value=str(request.source_material),
                log_impact=source_impacts[request.source_material],
                evidence=(
                    "A conservative historical prior; known-IP strength is modeled separately."
                ),
            )
        )

        franchise_impact = _clamp((request.franchise_strength - 20) / 100 * 0.32, -0.065, 0.255)
        factors.append(
            RawFactor(
                key="franchise_strength",
                label="Franchise / IP demand",
                value=f"{request.franchise_strength}/100",
                log_impact=franchise_impact,
                evidence=(
                    "Awareness prior supplied by the user, capped to avoid franchise certainty."
                ),
            )
        )

        release_impact = self._release_impact(request)
        factors.append(
            RawFactor(
                key="release_window",
                label="Release window",
                value=request.release_date.strftime("%b %d, %Y"),
                log_impact=release_impact,
                evidence="Genre-specific historical performance for the selected calendar month.",
            )
        )

        competition_impact = _clamp((45 - request.competition_score) / 100 * 0.36, -0.20, 0.16)
        factors.append(
            RawFactor(
                key="competition",
                label="Release competition",
                value=f"{request.competition_score}/100",
                log_impact=competition_impact,
                evidence="Opening-window cannibalization risk; lower competition is favorable.",
            )
        )

        ideal_runtime = (
            95 if Genre.HORROR in request.genres or Genre.COMEDY in request.genres else 115
        )
        runtime_distance = abs(request.runtime_minutes - ideal_runtime)
        runtime_impact = -min(0.13, max(0, runtime_distance - 12) * 0.0035)
        factors.append(
            RawFactor(
                key="runtime",
                label="Runtime fit",
                value=f"{request.runtime_minutes} min",
                log_impact=runtime_impact,
                evidence=f"Compared with a {ideal_runtime}-minute genre scheduling benchmark.",
            )
        )

        rating_impacts = {
            "G": 0.01,
            "PG": 0.055,
            "PG-13": 0.07,
            "R": -0.015,
            "NC-17": -0.22,
            "Not rated": -0.06,
        }
        factors.append(
            RawFactor(
                key="audience_rating",
                label="Audience accessibility",
                value=str(request.audience_rating),
                log_impact=rating_impacts[str(request.audience_rating)],
                evidence=(
                    "Theatrical audience-reach prior, adjusted conservatively by certification."
                ),
            )
        )

        distribution_impact = _clamp(0.20 * math.log(request.theater_count / 2800), -0.28, 0.19)
        factors.append(
            RawFactor(
                key="theater_count",
                label="Distribution scale",
                value=f"{request.theater_count:,} theaters",
                log_impact=distribution_impact,
                evidence="Diminishing-return wide-release effect relative to 2,800 locations.",
            )
        )

        premium_count = len(set(request.premium_formats) - {PremiumFormat.STANDARD})
        premium_impact = min(0.105, premium_count * 0.028)
        factors.append(
            RawFactor(
                key="premium_formats",
                label="Premium formats",
                value=", ".join(map(str, request.premium_formats)),
                log_impact=premium_impact,
                evidence="Premium-ticket and eventization lift, capped to avoid double counting.",
            )
        )

        factors.extend(
            [
                RawFactor(
                    key="social_buzz",
                    label="Social demand",
                    value=f"{request.social_buzz}/100",
                    log_impact=_clamp((request.social_buzz - 45) / 100 * 0.30, -0.135, 0.165),
                    evidence="Pre-release awareness and conversation momentum.",
                ),
                RawFactor(
                    key="trailer_engagement",
                    label="Trailer engagement",
                    value=f"{request.trailer_engagement}/100",
                    log_impact=_clamp(
                        (request.trailer_engagement - 40) / 100 * 0.20,
                        -0.08,
                        0.12,
                    ),
                    evidence="Engagement quality signal separated from raw awareness.",
                ),
                RawFactor(
                    key="international_appeal",
                    label="International appeal",
                    value=f"{request.international_appeal}/100",
                    log_impact=_clamp(
                        (request.international_appeal - 50) / 100 * 0.18,
                        -0.09,
                        0.09,
                    ),
                    evidence="Portability prior for markets outside the domestic release.",
                ),
                RawFactor(
                    key="production_readiness",
                    label="Production readiness",
                    value=f"{request.production_readiness}/100",
                    log_impact=_clamp(
                        (request.production_readiness - 60) / 100 * 0.13,
                        -0.078,
                        0.052,
                    ),
                    evidence="Schedule, package, and execution-risk proxy.",
                ),
                RawFactor(
                    key="market_regime",
                    label="Market regime",
                    value="2026 theatrical baseline",
                    log_impact=0.0,
                    evidence=(
                        "Neutral baseline pending live admissions, FX, and macro-market feeds."
                    ),
                    mutable=False,
                ),
            ]
        )
        return factors

    def _talent_factor(
        self,
        *,
        key: str,
        label: str,
        name: str | None,
        stats: dict[str, Any] | None,
        weight: float,
    ) -> RawFactor:
        if not name:
            return RawFactor(
                key=key,
                label=label,
                value="Unattached",
                log_impact=-0.055,
                evidence="Unattached package; the forecast carries added execution uncertainty.",
            )
        if not stats:
            return RawFactor(
                key=key,
                label=label,
                value=name,
                log_impact=-0.02,
                evidence="Name supplied, but no sufficiently reliable history matched.",
            )
        impact = _clamp(self._track_record(stats) * weight, -0.20, 0.26)
        return RawFactor(
            key=key,
            label=label,
            value=name,
            log_impact=impact,
            evidence=(
                f"{stats['films']} prior films, {_money(stats['median_revenue'])} median gross, "
                f"{stats['hit_rate']:.0%} historical hit rate."
            ),
        )

    def _track_record(self, stats: dict[str, Any]) -> float:
        global_revenue = float(self.knowledge.global_stats["median_revenue"])
        sample_weight = stats["films"] / (stats["films"] + 6)
        performance = math.log(max(0.1, stats["median_revenue"] / global_revenue))
        return _clamp(performance * sample_weight, -0.85, 1.0)

    def _release_impact(self, request: ForecastRequest) -> float:
        month = request.release_date.month
        impacts: list[float] = []
        for genre in request.genres:
            genre_stats = self.knowledge.genres.get(str(genre))
            month_stats = self.knowledge.genre_months.get(f"{genre}:{month}")
            if not genre_stats or not month_stats:
                continue
            genre_roi = genre_stats["median_revenue"] / max(1, genre_stats["median_budget"])
            month_roi = month_stats["median_revenue"] / max(1, month_stats["median_budget"])
            impacts.append(math.log(max(0.2, month_roi / genre_roi)))
        if impacts:
            return _clamp(sum(impacts) / len(impacts) * 0.18, -0.16, 0.16)
        return 0.0

    @staticmethod
    def _synopsis_signals(synopsis: str) -> list[SynopsisSignal]:
        words = re.findall(r"[A-Za-z']+", synopsis.casefold())
        word_count = len(words)
        unique_ratio = len(set(words)) / max(1, word_count)
        text = " ".join(words)

        protagonist_terms = {
            "woman",
            "man",
            "girl",
            "boy",
            "family",
            "detective",
            "scientist",
            "soldier",
            "artist",
            "mother",
            "father",
        }
        stakes_terms = {
            "must",
            "save",
            "survive",
            "before",
            "risk",
            "threat",
            "war",
            "death",
            "world",
            "secret",
            "fight",
        }
        hook_terms = {
            "discovers",
            "unexpected",
            "mysterious",
            "impossible",
            "last",
            "only",
            "hidden",
            "race",
            "trapped",
            "returns",
        }
        global_terms = {
            "world",
            "international",
            "planet",
            "ocean",
            "space",
            "future",
            "ancient",
            "kingdom",
            "city",
            "family",
        }

        clarity = 46
        clarity += 12 if 35 <= word_count <= 220 else -8
        clarity += min(18, sum(term in words for term in protagonist_terms) * 5)
        clarity += min(16, sum(term in words for term in stakes_terms) * 3)

        hook = 42 + min(34, sum(term in words for term in hook_terms) * 6)
        hook += 8 if "but" in words or "until" in words else 0

        specificity = 38 + round(unique_ratio * 38)
        specificity += 8 if re.search(r"\b(?:19|20)\d{2}\b", synopsis) else 0
        specificity += (
            6
            if any(
                token in text for token in ("new york", "los angeles", "london", "tokyo", "mumbai")
            )
            else 0
        )

        portability = 43 + min(30, sum(term in words for term in global_terms) * 5)
        portability += (
            8 if any(term in words for term in {"love", "family", "survive", "home"}) else 0
        )

        return [
            SynopsisSignal(
                label="Narrative clarity",
                score=round(_clamp(clarity, 15, 95)),
                detail="Identifiable protagonist, conflict, and stakes.",
            ),
            SynopsisSignal(
                label="Audience hook",
                score=round(_clamp(hook, 15, 95)),
                detail="Urgency, reversal, mystery, and promise of escalation.",
            ),
            SynopsisSignal(
                label="Specificity",
                score=round(_clamp(specificity, 15, 95)),
                detail="Concrete language and distinct story-world signals.",
            ),
            SynopsisSignal(
                label="Global portability",
                score=round(_clamp(portability, 15, 95)),
                detail="Themes and stakes likely to travel across markets.",
            ),
        ]

    @staticmethod
    def _uncertainty(request: ForecastRequest) -> float:
        if request.budget < 5_000_000:
            sigma = 0.78
        elif request.budget < 20_000_000:
            sigma = 0.68
        elif request.budget < 80_000_000:
            sigma = 0.58
        elif request.budget < 180_000_000:
            sigma = 0.53
        else:
            sigma = 0.49
        if not request.director:
            sigma += 0.05
        if not request.cast:
            sigma += 0.05
        if not request.studio:
            sigma += 0.04
        if request.source_material == SourceMaterial.ORIGINAL:
            sigma += 0.035
        return min(0.90, sigma)

    @staticmethod
    def _opening_share(request: ForecastRequest) -> float:
        if Genre.HORROR in request.genres:
            return 0.36
        if request.franchise_strength >= 65 or Genre.ACTION in request.genres:
            return 0.33
        if Genre.DRAMA in request.genres or Genre.DOCUMENTARY in request.genres:
            return 0.20
        return 0.27

    @staticmethod
    def _financials(
        *,
        request: ForecastRequest,
        low: float,
        expected: float,
        high: float,
        domestic_share: float,
        opening_share: float,
        sigma: float,
    ) -> FinancialOutcome:
        break_even = (request.budget + request.marketing_budget) / 0.58
        profit = expected * 0.58 - request.budget - request.marketing_budget
        invested = request.budget + request.marketing_budget
        distribution = NormalDist(mu=math.log(expected), sigma=sigma)
        break_even_probability = 1 - distribution.cdf(math.log(max(1, break_even)))
        hit_threshold = max(2 * request.budget, break_even)
        hit_probability = 1 - distribution.cdf(math.log(max(1, hit_threshold)))

        def scaled_range(scale: float) -> RevenueRange:
            return RevenueRange(low=low * scale, expected=expected * scale, high=high * scale)

        return FinancialOutcome(
            worldwide_gross=RevenueRange(low=low, expected=expected, high=high),
            domestic_gross=scaled_range(domestic_share),
            international_gross=scaled_range(1 - domestic_share),
            opening_weekend=scaled_range(domestic_share * opening_share),
            break_even_gross=break_even,
            expected_profit=profit,
            expected_roi=profit / invested,
            break_even_probability=break_even_probability,
            hit_probability=hit_probability,
        )

    @staticmethod
    def _factor_contributions(
        factors: list[RawFactor],
        expected: float,
    ) -> list[FactorContribution]:
        output = []
        for factor in factors:
            impact = expected * (math.exp(factor.log_impact) - 1)
            direction = (
                "positive"
                if impact > expected * 0.005
                else "negative"
                if impact < -expected * 0.005
                else "neutral"
            )
            output.append(
                FactorContribution(
                    key=factor.key,
                    label=factor.label,
                    value=factor.value,
                    impact=impact,
                    direction=direction,
                    evidence=factor.evidence,
                    mutable=factor.mutable,
                )
            )
        return output

    @staticmethod
    def _confidence(request: ForecastRequest, sigma: float) -> ConfidenceResult:
        supplied = [
            bool(request.director),
            bool(request.cast),
            bool(request.studio),
            request.marketing_budget > 0,
            request.theater_count > 0,
            request.social_buzz > 0,
            request.trailer_engagement > 0,
        ]
        completeness = sum(supplied) / len(supplied)
        score = round(_clamp(100 - sigma * 70 + completeness * 15, 28, 88))
        level: Literal["Low", "Medium", "High"] = (
            "High" if score >= 75 else "Medium" if score >= 52 else "Low"
        )
        segment = (
            "Micro"
            if request.budget < 5_000_000
            else "Low"
            if request.budget < 20_000_000
            else "Mid"
            if request.budget < 80_000_000
            else "High"
            if request.budget < 180_000_000
            else "Blockbuster"
        )
        caveats = [
            (
                "Ranges exclude black-swan events, release delays, and major changes in "
                "market capacity."
            ),
            "Marketing and social inputs are user estimates until live connectors are configured.",
        ]
        if not request.director or not request.cast or not request.studio:
            caveats.append(
                "One or more package elements are unattached, increasing execution uncertainty."
            )
        return ConfidenceResult(
            score=score,
            level=level,
            data_completeness=completeness,
            calibration_segment=segment,
            caveats=caveats,
        )

    @staticmethod
    def _robustness(
        request: ForecastRequest,
        expected: float,
        sigma: float,
        factors: list[FactorContribution],
    ) -> RobustnessResult:
        seed_material = (
            f"{request.title}|{request.budget}|{request.release_date.isoformat()}|"
            f"{','.join(map(str, request.genres))}|{request.director}|{request.studio}"
        )
        seed = int(hashlib.sha256(seed_material.encode()).hexdigest()[:16], 16)
        rng = random.Random(seed)  # noqa: S311 - deterministic simulation, not security
        outcomes: list[float] = []
        profitable = 0
        invested = request.budget + request.marketing_budget
        for _ in range(600):
            gross = rng.lognormvariate(math.log(expected), sigma)
            cost = invested * rng.triangular(0.92, 1.18, 1.0)
            outcomes.append(gross)
            profitable += int(gross * 0.58 > cost)
        outcomes.sort()
        profitable_share = profitable / len(outcomes)
        score = round(_clamp(profitable_share * 76 + (1 - sigma) * 24, 0, 100))
        label: Literal["Fragile", "Mixed", "Resilient"] = (
            "Resilient" if score >= 72 else "Mixed" if score >= 46 else "Fragile"
        )
        negative = [factor for factor in factors if factor.impact < 0]
        negative.sort(key=lambda factor: factor.impact)
        key_risk = negative[0].label if negative else "Market volatility"
        return RobustnessResult(
            score=score,
            label=label,
            profitable_scenarios=profitable_share,
            downside_gross=outcomes[59],
            upside_gross=outcomes[539],
            key_risk=key_risk,
        )


def _money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
