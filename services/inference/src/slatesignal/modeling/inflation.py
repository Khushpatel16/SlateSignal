from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path
from statistics import mean

BASE_YEAR = 2025
PROJECTED_ANNUAL_INFLATION = 0.024


@lru_cache
def annual_cpi(path: str | Path) -> dict[int, float]:
    grouped: dict[int, list[float]] = {}
    with Path(path).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            raw = row.get("DATE") or row.get("observation_date")
            value = row.get("CPIAUCSL")
            if not raw or not value or value == ".":
                continue
            grouped.setdefault(int(raw[:4]), []).append(float(value))
    return {year: mean(values) for year, values in grouped.items() if values}


def cpi_for_year(values: dict[int, float], year: int) -> float:
    if year in values:
        return values[year]
    latest_year = max(values)
    latest = values[latest_year]
    if year > latest_year:
        return latest * (1 + PROJECTED_ANNUAL_INFLATION) ** (year - latest_year)
    earliest_year = min(values)
    return values[earliest_year] if year < earliest_year else values[BASE_YEAR]


def to_base_year_dollars(
    amount: float,
    *,
    year: int,
    values: dict[int, float],
) -> float:
    return amount * cpi_for_year(values, BASE_YEAR) / cpi_for_year(values, year)


def from_base_year_dollars(
    amount: float,
    *,
    year: int,
    values: dict[int, float],
) -> float:
    return amount * cpi_for_year(values, year) / cpi_for_year(values, BASE_YEAR)
