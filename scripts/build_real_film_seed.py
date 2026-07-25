"""Build the deployable real-film launch snapshot from the research corpus.

The launch snapshot is intentionally not a replacement for the TMDB catalog job.
It gives local development a source-backed dataset without shipping the ignored
research CSVs or inventing films when credentials are absent.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "master_1970_2025_clean.csv"
OUTPUT = ROOT / "services" / "inference" / "data" / "real_film_seed.json"
OBSERVED_AT = "2025-11-27T00:00:00+00:00"

GENRE_MAP = {
    "action": "Action",
    "adventure": "Adventure",
    "animation": "Animation",
    "comedy": "Comedy",
    "crime": "Crime",
    "documentary": "Documentary",
    "drama": "Drama",
    "family": "Family",
    "fantasy": "Fantasy",
    "history": "History",
    "horror": "Horror",
    "music": "Music",
    "mystery": "Mystery",
    "romance": "Romance",
    "sci-fi": "Science Fiction",
    "science fiction": "Science Fiction",
    "thriller": "Thriller",
    "war": "War",
    "western": "Western",
}

OFFICIAL_UPCOMING: list[dict[str, Any]] = [
    {
        "slug": "spider-man-brand-new-day-2026",
        "title": "Spider-Man: Brand New Day",
        "release_status": "confirmed",
        "release_date": "2026-07-31",
        "release_year": 2026,
        "date_precision": "day",
        "synopsis": (
            "Peter Parker fights crime full-time in a world that no longer remembers him. "
            "Watching his former friends move forward triggers a dangerous transformation "
            "as an unseen new threat closes in on New York."
        ),
        "genres": ["Action", "Adventure", "Science Fiction"],
        "director": "Destin Daniel Cretton",
        "cast": [
            "Tom Holland",
            "Zendaya",
            "Sadie Sink",
            "Jacob Batalon",
            "Jon Bernthal",
        ],
        "companies": ["Columbia Pictures", "Marvel Studios", "Pascal Pictures"],
        "poster_url": "/films/spider-man-brand-new-day.jpg",
        "source": "sony_pictures",
        "source_url": "https://www.sonypictures.com/movies/spidermanbrandnewday",
        "source_confidence": 1.0,
        "observed_at": "2026-07-24T00:00:00+00:00",
        "notes": ["US theatrical date and creative package confirmed by the distributor."],
    },
    {
        "slug": "avengers-doomsday-2026",
        "title": "Avengers: Doomsday",
        "release_status": "confirmed",
        "release_date": "2026-12-18",
        "release_year": 2026,
        "date_precision": "day",
        "synopsis": None,
        "genres": ["Action", "Adventure", "Science Fiction"],
        "director": "Anthony Russo",
        "additional_directors": ["Joe Russo"],
        "cast": ["Robert Downey Jr.", "Chris Evans", "Chris Hemsworth"],
        "companies": ["Marvel Studios", "Walt Disney Studios Motion Pictures"],
        "source": "marvel",
        "source_url": "https://www.marvel.com/movies/avengers-doomsday",
        "source_confidence": 1.0,
        "observed_at": "2026-07-24T00:00:00+00:00",
        "trailer_url": "https://www.youtube.com/watch?v=399Ez7WHK5s",
        "notes": ["Official synopsis has not been published; SlateSignal leaves it unavailable."],
    },
    {
        "slug": "dune-part-three-2026",
        "title": "Dune: Part Three",
        "release_status": "confirmed",
        "release_date": "2026-12-18",
        "release_year": 2026,
        "date_precision": "day",
        "synopsis": (
            "Years after Paul Atreides takes the imperial throne, the consequences of his "
            "holy war and a conspiracy around his rule force him to confront the cost of "
            "prescience, power, and legacy."
        ),
        "genres": ["Science Fiction", "Adventure", "Drama"],
        "director": "Denis Villeneuve",
        "cast": [
            "Timothee Chalamet",
            "Zendaya",
            "Florence Pugh",
            "Jason Momoa",
            "Anya Taylor-Joy",
        ],
        "companies": ["Legendary Entertainment", "Warner Bros. Pictures"],
        "poster_url": "/films/dune-part-three.jpg",
        "backdrop_url": "/films/dune-part-three-wide.jpg",
        "source": "legendary",
        "source_url": "https://www.legendary.com/film/dune-part-three/",
        "source_confidence": 0.95,
        "observed_at": "2026-07-24T00:00:00+00:00",
        "notes": [
            "North American theatrical release is confirmed for December 18, 2026.",
            "IMAX presentation is confirmed; other premium-format coverage awaits catalog sync.",
        ],
    },
    {
        "slug": "spider-man-beyond-the-spider-verse-2027",
        "title": "Spider-Man: Beyond the Spider-Verse",
        "release_status": "confirmed",
        "release_date": "2027-06-18",
        "release_year": 2027,
        "date_precision": "day",
        "synopsis": (
            "Miles Morales remains stranded in a reality where his counterpart became the "
            "Prowler, while his allies race across the multiverse to bring him home."
        ),
        "genres": ["Animation", "Action", "Adventure"],
        "director": "Bob Persichetti",
        "additional_directors": ["Justin K. Thompson"],
        "cast": [],
        "companies": ["Sony Pictures Animation", "Columbia Pictures"],
        "source": "marvel",
        "source_url": (
            "https://www.marvel.com/articles/movies/spider-man-brand-new-day-teaser-"
            "posters-spider-man-beyond-the-spider-verse-stills-cinemacon-2026"
        ),
        "source_confidence": 1.0,
        "observed_at": "2026-07-24T00:00:00+00:00",
        "notes": ["US theatrical date confirmed in the official CinemaCon announcement."],
    },
    {
        "slug": "avengers-secret-wars-2027",
        "title": "Avengers: Secret Wars",
        "release_status": "confirmed",
        "release_date": "2027-12-17",
        "release_year": 2027,
        "date_precision": "day",
        "synopsis": None,
        "genres": ["Action", "Adventure", "Science Fiction"],
        "director": "Anthony Russo",
        "additional_directors": ["Joe Russo"],
        "cast": ["Robert Downey Jr."],
        "companies": ["Marvel Studios", "Walt Disney Studios Motion Pictures"],
        "source": "marvel",
        "source_url": "https://www.marvel.com/movies/avengers-secret-wars",
        "source_confidence": 1.0,
        "observed_at": "2026-07-24T00:00:00+00:00",
        "notes": ["Official synopsis has not been published; SlateSignal leaves it unavailable."],
    },
]


def _list(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        value = ast.literal_eval(raw)
    except (SyntaxError, ValueError):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _genres(raw: str) -> list[str]:
    output: list[str] = []
    for value in _list(raw):
        normalized = value.casefold()
        match = next(
            (canonical for key, canonical in GENRE_MAP.items() if key in normalized),
            None,
        )
        if match and match not in output:
            output.append(match)
    return output[:5] or ["Other"]


def _release_date(raw: str, year: int) -> tuple[str | None, str]:
    match = re.search(
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December)\s+(\d{1,2}),\s+(\d{4})",
        raw,
    )
    if match:
        parsed = datetime.strptime(match.group(0), "%B %d, %Y").replace(tzinfo=UTC).date()
        return parsed.isoformat(), "day"
    return None, "year"


def _slug(title: str, year: int, imdb_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    suffix = imdb_id.removeprefix("tt") if imdb_id else ""
    return f"{normalized}-{year}-{suffix}".rstrip("-")


def _imdb_id(url: str) -> str:
    match = re.search(r"/title/(tt\d+)", url)
    return match.group(1) if match else ""


def historical_records() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    with SOURCE.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            year = int(float(row["year"]))
            if year < 2021:
                continue
            imdb_id = _imdb_id(row.get("imdb_link", ""))
            release_date, precision = _release_date(row.get("release_date", ""), year)
            budget = float(row["budget"]) if row.get("budget") else None
            revenue = float(row["revenue"]) if row.get("revenue") else None
            output.append(
                {
                    "slug": _slug(row["title"], year, imdb_id),
                    "title": row["title"],
                    "original_title": None,
                    "release_status": "gross_closed" if revenue else "released",
                    "release_date": release_date,
                    "release_year": year,
                    "date_precision": precision,
                    "synopsis": row.get("description_short") or row.get("plot_text") or None,
                    "genres": _genres(row.get("genres_raw", "")),
                    "runtime": row.get("duration") or None,
                    "certification": row.get("MPA") or None,
                    "budget": budget,
                    "budget_status": "reported" if budget else "unavailable",
                    "director": row.get("director_name") or None,
                    "cast": _list(row.get("cast_raw", ""))[:5],
                    "companies": _list(row.get("production_company", ""))[:5],
                    "external_ids": {"imdb": imdb_id} if imdb_id else {},
                    "actuals": (
                        [
                            {
                                "target": "worldwide_total",
                                "amount": revenue,
                                "currency": "USD",
                                "amount_status": "final",
                            }
                        ]
                        if revenue
                        else []
                    ),
                    "source": "research_corpus",
                    "source_url": row.get("imdb_link") or "urn:slatesignal:research-corpus",
                    "source_confidence": 0.72,
                    "observed_at": OBSERVED_AT,
                    "notes": [
                        "Included in the original 6,437-film research corpus.",
                        "This launch snapshot is not the exhaustive TMDB theatrical catalog.",
                    ],
                }
            )
    return output


def main() -> int:
    if not SOURCE.exists():
        print(f"Missing research corpus: {SOURCE}", file=sys.stderr)
        return 1
    movies = historical_records() + OFFICIAL_UPCOMING
    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": (
            "Source-backed local launch snapshot. Run `slatesignal jobs catalog-sync` with "
            "TMDB_API_TOKEN for the complete 2021-2030 US theatrical catalog."
        ),
        "sources": [
            "research_corpus",
            "sony_pictures",
            "marvel",
            "legendary",
        ],
        "movies": movies,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")
    checksum = hashlib.sha256(rendered.encode()).hexdigest()
    print(f"Wrote {len(movies):,} real films to {OUTPUT}")
    print(f"SHA-256 {checksum}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
