from calendar import monthrange
from datetime import date
from typing import TypedDict

from slatesignal.domain.schemas import (
    AudienceRating,
    ForecastRequest,
    Genre,
    OptimizeRequest,
    OptimizeResponse,
    PlanRecommendation,
    PremiumFormat,
    SourceMaterial,
)
from slatesignal.services.forecast import ForecastEngine
from slatesignal.services.knowledge import KnowledgeBase, get_knowledge_base


class PlanProfile(TypedDict):
    id: str
    label: str
    thesis: str
    budget: float
    marketing: float
    theaters: int
    formats: list[PremiumFormat]
    competition: int
    social: int
    readiness: int
    person_index: int


class GreenlightOptimizer:
    def __init__(
        self,
        engine: ForecastEngine | None = None,
        knowledge: KnowledgeBase | None = None,
    ) -> None:
        self.knowledge = knowledge or get_knowledge_base()
        self.engine = engine or ForecastEngine(self.knowledge)

    def optimize(self, request: OptimizeRequest) -> OptimizeResponse:
        catalog = self.knowledge.search("", request.genres, limit=12)
        directors = [person for person in catalog.people if person.role == "director"]
        actors = [person for person in catalog.people if person.role == "cast"]
        studios = catalog.studios
        release_dates = self._release_candidates(request)
        base_budget = request.target_budget or self._genre_budget(request.genres)

        profiles: list[PlanProfile] = [
            {
                "id": "precision",
                "label": "Precision play",
                "thesis": (
                    "Protect downside with a focused package and disciplined theatrical footprint."
                ),
                "budget": base_budget * 0.68,
                "marketing": 0.38,
                "theaters": 1900,
                "formats": [PremiumFormat.STANDARD, PremiumFormat.DOLBY],
                "competition": 30,
                "social": 42,
                "readiness": 78,
                "person_index": 0,
            },
            {
                "id": "balanced",
                "label": "Commercial balance",
                "thesis": (
                    "Maximize expected profit without making the outcome depend on "
                    "event-scale demand."
                ),
                "budget": base_budget,
                "marketing": 0.48,
                "theaters": 3100,
                "formats": [PremiumFormat.STANDARD, PremiumFormat.DOLBY, PremiumFormat.IMAX],
                "competition": 38,
                "social": 52,
                "readiness": 72,
                "person_index": 1,
            },
            {
                "id": "event",
                "label": "Event swing",
                "thesis": (
                    "Buy global reach and premium-format upside while accepting a wider "
                    "downside range."
                ),
                "budget": base_budget * 1.52,
                "marketing": 0.62,
                "theaters": 4200,
                "formats": [
                    PremiumFormat.STANDARD,
                    PremiumFormat.DOLBY,
                    PremiumFormat.IMAX,
                    PremiumFormat.THREE_D,
                ],
                "competition": 46,
                "social": 64,
                "readiness": 66,
                "person_index": 2,
            },
        ]

        plans: list[PlanRecommendation] = []
        for index, profile in enumerate(profiles):
            person_index = min(profile["person_index"], max(0, len(directors) - 1))
            director = request.fixed_director or (
                directors[person_index].name if directors else None
            )
            suggested_cast = list(request.fixed_cast)
            for actor in actors[index : index + 3]:
                if actor.name not in suggested_cast:
                    suggested_cast.append(actor.name)
                if len(suggested_cast) >= 4:
                    break
            studio = studios[index].name if index < len(studios) else None
            budget = min(500_000_000, max(100_000, float(profile["budget"])))
            forecast_request = ForecastRequest(
                title=request.title,
                synopsis=request.synopsis,
                genres=request.genres,
                budget=budget,
                marketing_budget=budget * float(profile["marketing"]),
                release_date=release_dates[index],
                runtime_minutes=self._runtime(request.genres, index),
                audience_rating=self._rating(request.genres),
                director=director,
                cast=suggested_cast,
                studio=studio,
                source_material=SourceMaterial.ORIGINAL,
                franchise_strength=8 if index < 2 else 18,
                premium_formats=profile["formats"],
                theater_count=int(profile["theaters"]),
                competition_score=int(profile["competition"]),
                social_buzz=int(profile["social"]),
                trailer_engagement=int(profile["social"]) - 5,
                international_appeal=self._international_appeal(request.genres, index),
                production_readiness=int(profile["readiness"]),
            )
            forecast = self.engine.predict(forecast_request)
            reasons = [
                (
                    f"{release_dates[index].strftime('%B %Y')} is one of the strongest "
                    "available genre windows."
                ),
                (
                    f"{director} offers the best available genre/track-record fit."
                    if director
                    else "Director remains open so the package carries additional uncertainty."
                ),
                (
                    f"The plan targets a {forecast.robustness.label.lower()} risk profile with "
                    f"{forecast.robustness.profitable_scenarios:.0%} profitable simulations."
                ),
            ]
            plans.append(
                PlanRecommendation(
                    id=str(profile["id"]),
                    label=str(profile["label"]),
                    thesis=str(profile["thesis"]),
                    request=forecast_request,
                    forecast=forecast,
                    reasons=reasons,
                )
            )

        recommendation_index = {
            "conservative": 0,
            "balanced": 1,
            "aggressive": 2,
        }[request.risk_tolerance]
        preferred = plans[recommendation_index]
        notes = []
        if request.fixed_director:
            notes.append(f"Director locked to {request.fixed_director}.")
        if request.fixed_cast:
            notes.append(f"{len(request.fixed_cast)} cast choice(s) preserved across all plans.")
        if request.target_budget:
            notes.append("Budget variants are centered on the supplied target.")

        return OptimizeResponse(
            plans=plans,
            recommendation=(
                f"{preferred.label} best matches the selected {request.risk_tolerance} risk "
                "posture. Compare the robustness score and downside range before treating "
                "expected gross as the decision."
            ),
            constraint_notes=notes,
        )

    def _release_candidates(self, request: OptimizeRequest) -> list[date]:
        candidates: list[tuple[float, date]] = []
        cursor = date(request.earliest_release.year, request.earliest_release.month, 1)
        end = date(request.latest_release.year, request.latest_release.month, 1)
        while cursor <= end:
            first_friday = self._first_friday(cursor.year, cursor.month)
            if request.earliest_release <= first_friday <= request.latest_release:
                synthetic = ForecastRequest(
                    title=request.title,
                    synopsis=request.synopsis,
                    genres=request.genres,
                    budget=request.target_budget or self._genre_budget(request.genres),
                    release_date=first_friday,
                )
                score = self.engine._release_impact(synthetic)
                candidates.append((score, first_friday))
            next_month = cursor.month % 12 + 1
            next_year = cursor.year + int(next_month == 1)
            cursor = date(next_year, next_month, 1)

        candidates.sort(key=lambda item: (-item[0], item[1]))
        selected: list[date] = []
        for _, candidate in candidates:
            if all(abs((candidate - chosen).days) >= 35 for chosen in selected):
                selected.append(candidate)
            if len(selected) == 3:
                break
        while len(selected) < 3:
            offset = len(selected)
            month = min(12, request.earliest_release.month + offset * 2)
            day = min(
                request.earliest_release.day, monthrange(request.earliest_release.year, month)[1]
            )
            fallback = date(request.earliest_release.year, month, day)
            selected.append(min(request.latest_release, max(request.earliest_release, fallback)))
        return selected

    @staticmethod
    def _first_friday(year: int, month: int) -> date:
        first = date(year, month, 1)
        return date(year, month, 1 + (4 - first.weekday()) % 7)

    def _genre_budget(self, genres: list[Genre]) -> float:
        budgets = [
            self.knowledge.genres[str(genre)]["median_budget"]
            for genre in genres
            if str(genre) in self.knowledge.genres
        ]
        return sum(budgets) / len(budgets) if budgets else 35_000_000

    @staticmethod
    def _runtime(genres: list[Genre], variant: int) -> int:
        base = 96 if Genre.HORROR in genres or Genre.COMEDY in genres else 112
        return base + variant * 7

    @staticmethod
    def _rating(genres: list[Genre]) -> AudienceRating:
        if Genre.FAMILY in genres or Genre.ANIMATION in genres:
            return AudienceRating.PG
        if Genre.HORROR in genres:
            return AudienceRating.R
        return AudienceRating.PG13

    @staticmethod
    def _international_appeal(genres: list[Genre], variant: int) -> int:
        base = (
            66
            if any(
                genre in genres
                for genre in (Genre.ACTION, Genre.ADVENTURE, Genre.ANIMATION, Genre.FANTASY)
            )
            else 52
        )
        return min(90, base + variant * 7)
