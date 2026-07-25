#!/usr/bin/env python3
"""Build the compact runtime knowledge base from released-film CSV data."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import strptime
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "full_dataset_with_gender.csv"
DEFAULT_OUTPUT = ROOT / "services" / "inference" / "data" / "knowledge_base.json"

GENRE_ALIASES = {
    "sci-fi": "Science Fiction",
    "science fiction": "Science Fiction",
    "dark comedy": "Comedy",
    "romantic comedy": "Romance",
    "supernatural horror": "Horror",
    "period drama": "Drama",
    "biography": "Drama",
}
CANONICAL_GENRES = {
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
}


@dataclass
class Stats:
    revenues: list[float] = field(default_factory=list)
    budgets: list[float] = field(default_factory=list)
    hits: int = 0
    genres: Counter[str] = field(default_factory=Counter)
    latest_year: int = 0

    def add(
        self, *, revenue: float, budget: float, hit: bool, genres: list[str], year: int
    ) -> None:
        self.revenues.append(revenue)
        self.budgets.append(budget)
        self.hits += int(hit)
        self.genres.update(genres)
        self.latest_year = max(self.latest_year, year)

    def summary(self) -> dict[str, Any]:
        count = len(self.revenues)
        trimmed = _trimmed(self.revenues)
        return {
            "films": count,
            "avg_revenue": round(statistics.fmean(trimmed), 2),
            "median_revenue": round(statistics.median(self.revenues), 2),
            "median_budget": round(statistics.median(self.budgets), 2),
            "hit_rate": round(self.hits / count, 4),
            "latest_year": self.latest_year,
            "genres": dict(self.genres.most_common(8)),
        }


def _trimmed(values: list[float], proportion: float = 0.08) -> list[float]:
    if len(values) < 10:
        return values
    ordered = sorted(values)
    trim = max(1, round(len(ordered) * proportion))
    return ordered[trim:-trim]


def _safe_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _safe_int(value: str | None) -> int | None:
    number = _safe_float(value)
    return int(number) if number is not None else None


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        return [part.strip() for part in value.split(",") if part.strip()]
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _genres(value: str | None) -> list[str]:
    output: list[str] = []
    for raw in _parse_list(value):
        alias = GENRE_ALIASES.get(raw.casefold(), raw)
        if alias in CANONICAL_GENRES and alias not in output:
            output.append(alias)
    return output or ["Drama"]


def _release_month(value: str | None) -> int | None:
    if not value:
        return None
    for pattern in ("%B %d, %Y", "%b %d, %Y", "%Y-%m-%d"):
        try:
            return strptime(value.strip(), pattern).tm_mon
        except ValueError:
            continue
    return None


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def build(input_path: Path) -> dict[str, Any]:
    directors: defaultdict[str, Stats] = defaultdict(Stats)
    cast: defaultdict[str, Stats] = defaultdict(Stats)
    studios: defaultdict[str, Stats] = defaultdict(Stats)
    genre_stats: defaultdict[str, Stats] = defaultdict(Stats)
    month_stats: defaultdict[str, Stats] = defaultdict(Stats)
    genre_month_stats: defaultdict[str, Stats] = defaultdict(Stats)
    revenues: list[float] = []
    budgets: list[float] = []
    accepted_rows = 0

    with input_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            revenue = _safe_float(row.get("revenue"))
            budget = _safe_float(row.get("budget"))
            year = _safe_int(row.get("year"))
            if not revenue or not budget or not year or revenue <= 0 or budget <= 0:
                continue

            genres = _genres(row.get("genres_raw"))
            hit = revenue >= budget * 2
            director = (row.get("director_name") or "").strip()
            names = _parse_list(row.get("cast_raw"))[:6]
            companies = _parse_list(row.get("production_company"))[:4]
            month = _release_month(row.get("release_date"))
            accepted_rows += 1
            revenues.append(revenue)
            budgets.append(budget)

            if director:
                directors[director].add(
                    revenue=revenue,
                    budget=budget,
                    hit=hit,
                    genres=genres,
                    year=year,
                )
            for name in names:
                cast[name].add(
                    revenue=revenue,
                    budget=budget,
                    hit=hit,
                    genres=genres,
                    year=year,
                )
            for company in companies:
                studios[company].add(
                    revenue=revenue,
                    budget=budget,
                    hit=hit,
                    genres=genres,
                    year=year,
                )
            for genre in genres:
                genre_stats[genre].add(
                    revenue=revenue,
                    budget=budget,
                    hit=hit,
                    genres=genres,
                    year=year,
                )
                if month:
                    genre_month_stats[f"{genre}:{month}"].add(
                        revenue=revenue,
                        budget=budget,
                        hit=hit,
                        genres=genres,
                        year=year,
                    )
            if month:
                month_stats[str(month)].add(
                    revenue=revenue,
                    budget=budget,
                    hit=hit,
                    genres=genres,
                    year=year,
                )

    def ranked(source: dict[str, Stats], minimum: int, limit: int) -> dict[str, Any]:
        eligible = [
            (name, stats) for name, stats in source.items() if len(stats.revenues) >= minimum
        ]
        eligible.sort(
            key=lambda item: (
                math.log1p(len(item[1].revenues)) * statistics.fmean(_trimmed(item[1].revenues)),
                item[0],
            ),
            reverse=True,
        )
        return {name: stats.summary() for name, stats in eligible[:limit]}

    return {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "source": str(input_path.relative_to(ROOT)),
        "rows": accepted_rows,
        "global": {
            "median_revenue": round(statistics.median(revenues), 2),
            "mean_revenue": round(statistics.fmean(_trimmed(revenues)), 2),
            "median_budget": round(statistics.median(budgets), 2),
            "revenue_percentiles": {
                "p10": round(_percentile(revenues, 0.10), 2),
                "p50": round(_percentile(revenues, 0.50), 2),
                "p90": round(_percentile(revenues, 0.90), 2),
            },
        },
        "directors": ranked(directors, minimum=2, limit=400),
        "cast": ranked(cast, minimum=3, limit=800),
        "studios": ranked(studios, minimum=3, limit=400),
        "genres": {name: stats.summary() for name, stats in sorted(genre_stats.items())},
        "months": {name: stats.summary() for name, stats in sorted(month_stats.items())},
        "genre_months": {
            name: stats.summary()
            for name, stats in sorted(genre_month_stats.items())
            if len(stats.revenues) >= 5
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    payload = build(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} with {payload['rows']:,} released films")


if __name__ == "__main__":
    main()
