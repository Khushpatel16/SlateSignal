import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from slatesignal.core.config import get_settings
from slatesignal.domain.schemas import CatalogSearchResponse, Genre, PersonOption, StudioOption


class KnowledgeBase:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.global_stats: dict[str, Any] = payload["global"]
        self.directors: dict[str, dict[str, Any]] = payload.get("directors", {})
        self.cast: dict[str, dict[str, Any]] = payload.get("cast", {})
        self.studios: dict[str, dict[str, Any]] = payload.get("studios", {})
        self.genres: dict[str, dict[str, Any]] = payload.get("genres", {})
        self.months: dict[str, dict[str, Any]] = payload.get("months", {})
        self.genre_months: dict[str, dict[str, Any]] = payload.get("genre_months", {})
        self._director_index = {name.casefold(): name for name in self.directors}
        self._cast_index = {name.casefold(): name for name in self.cast}
        self._studio_index = {name.casefold(): name for name in self.studios}

    @classmethod
    def load(cls, path: str | Path) -> "KnowledgeBase":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(payload)

    def director(self, name: str | None) -> dict[str, Any] | None:
        return self._lookup(name, self.directors, self._director_index)

    def actor(self, name: str | None) -> dict[str, Any] | None:
        return self._lookup(name, self.cast, self._cast_index)

    def studio(self, name: str | None) -> dict[str, Any] | None:
        return self._lookup(name, self.studios, self._studio_index)

    @staticmethod
    def _lookup(
        name: str | None,
        source: dict[str, dict[str, Any]],
        index: dict[str, str],
    ) -> dict[str, Any] | None:
        if not name:
            return None
        canonical = index.get(name.strip().casefold())
        return source.get(canonical) if canonical else None

    @staticmethod
    def _genre_fit(stats: dict[str, Any], genres: list[Genre]) -> float:
        counts = stats.get("genres")
        if not isinstance(counts, dict):
            return 0.0
        total = sum(_number(value) for value in counts.values())
        if not total:
            return 0.0
        matched = sum(_number(counts.get(str(genre), 0)) for genre in genres)
        return min(1.0, matched / max(1, total) * 2.5)

    def search(self, query: str, genres: list[Genre], limit: int = 8) -> CatalogSearchResponse:
        needle = query.strip().casefold()

        def people_from(
            source: dict[str, dict[str, Any]],
            role: Literal["director", "cast"],
        ) -> list[PersonOption]:
            matches: list[tuple[float, PersonOption]] = []
            for name, stats in source.items():
                if needle and needle not in name.casefold():
                    continue
                genre_fit = self._genre_fit(stats, genres)
                films = int(_number(stats.get("films")))
                hit_rate = _number(stats.get("hit_rate"))
                avg_revenue = _number(stats.get("avg_revenue"))
                score = (
                    genre_fit * 3
                    + min(1.0, films / 12)
                    + hit_rate
                    + min(1.5, avg_revenue / 250_000_000)
                )
                matches.append(
                    (
                        score,
                        PersonOption(
                            name=name,
                            role=role,
                            films=films,
                            avg_revenue=avg_revenue,
                            hit_rate=hit_rate,
                            genre_fit=genre_fit,
                        ),
                    )
                )
            matches.sort(key=lambda item: (-item[0], item[1].name))
            return [item[1] for item in matches[:limit]]

        studio_matches: list[tuple[float, StudioOption]] = []
        for name, stats in self.studios.items():
            if needle and needle not in name.casefold():
                continue
            genre_fit = self._genre_fit(stats, genres)
            films = int(_number(stats.get("films")))
            hit_rate = _number(stats.get("hit_rate"))
            avg_revenue = _number(stats.get("avg_revenue"))
            score = (
                genre_fit * 3
                + min(1.0, films / 20)
                + hit_rate
                + min(1.5, avg_revenue / 300_000_000)
            )
            studio_matches.append(
                (
                    score,
                    StudioOption(
                        name=name,
                        films=films,
                        avg_revenue=avg_revenue,
                        hit_rate=hit_rate,
                        genre_fit=genre_fit,
                    ),
                )
            )
        studio_matches.sort(key=lambda item: (-item[0], item[1].name))

        people = people_from(self.directors, "director")
        people.extend(people_from(self.cast, "cast"))
        return CatalogSearchResponse(
            people=people,
            studios=[item[1] for item in studio_matches[:limit]],
        )


@lru_cache
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase.load(get_settings().knowledge_base_path)


def _number(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0
