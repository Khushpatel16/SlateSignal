from __future__ import annotations

import csv
import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from slatesignal.core.config import Settings, get_settings
from slatesignal.domain.models import Credit, Movie, Person
from slatesignal.services.provenance import record_observation

IMDB_DATASETS = "https://datasets.imdbws.com"
IMDB_DATASET_PAGE = "https://developer.imdb.com/non-commercial-datasets/"
FILES = (
    "title.basics.tsv.gz",
    "title.crew.tsv.gz",
    "title.principals.tsv.gz",
    "name.basics.tsv.gz",
)


class ImdbDatasetSync:
    """Join the public non-commercial IMDb snapshots to known catalog titles."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.cache = Path(self.settings.imdb_cache_dir)

    async def sync(self, *, refresh: bool = False) -> dict[str, int]:
        movies = list(
            self.db.scalars(select(Movie).options(selectinload(Movie.external_ids))).unique()
        )
        by_tconst = {
            item.external_id: movie
            for movie in movies
            for item in movie.external_ids
            if item.source == "imdb"
        }
        stats = {
            "known_imdb_titles": len(by_tconst),
            "titles_enriched": 0,
            "credits_added": 0,
            "files_downloaded": 0,
        }
        if not by_tconst:
            return stats

        self.cache.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, read=600.0),
            headers={"User-Agent": "SlateSignal/0.2 non-commercial research"},
            follow_redirects=True,
        ) as client:
            for filename in FILES:
                stats["files_downloaded"] += int(
                    await self._download(client, filename, refresh=refresh)
                )

        title_rows = self._matching_rows(
            self.cache / "title.basics.tsv.gz",
            "tconst",
            set(by_tconst),
        )
        crew_rows = self._matching_rows(
            self.cache / "title.crew.tsv.gz",
            "tconst",
            set(by_tconst),
        )
        principal_rows = self._matching_rows(
            self.cache / "title.principals.tsv.gz",
            "tconst",
            set(by_tconst),
            multiple=True,
        )

        needed_people: set[str] = set()
        for row in crew_rows.values():
            needed_people.update(_ids(row.get("directors")))
            needed_people.update(_ids(row.get("writers")))
        for rows in principal_rows.values():
            needed_people.update(
                str(row["nconst"]) for row in rows if row.get("nconst") not in {None, r"\N"}
            )
        people = self._matching_rows(
            self.cache / "name.basics.tsv.gz",
            "nconst",
            needed_people,
        )

        observed_at = datetime.now(UTC)
        for tconst, movie in by_tconst.items():
            basics = title_rows.get(tconst)
            if basics:
                self._enrich_movie(movie, basics)
                stats["titles_enriched"] += 1
            stats["credits_added"] += self._credits(
                movie,
                crew_rows.get(tconst, {}),
                principal_rows.get(tconst, []),
                people,
            )
            record_observation(
                self.db,
                movie_id=movie.id,
                source="imdb_datasets",
                observation_type="canonical_title_credits",
                observed_at=observed_at,
                source_url=IMDB_DATASET_PAGE,
                confidence=0.90,
                payload={
                    "tconst": tconst,
                    "basics": basics,
                    "crew": crew_rows.get(tconst),
                    "principals": principal_rows.get(tconst, []),
                    "dataset_snapshot": observed_at.date().isoformat(),
                },
            )
        self.db.commit()
        return stats

    async def _download(
        self,
        client: httpx.AsyncClient,
        filename: str,
        *,
        refresh: bool,
    ) -> bool:
        destination = self.cache / filename
        fresh_after = datetime.now(UTC) - timedelta(days=6)
        if (
            destination.exists()
            and not refresh
            and datetime.fromtimestamp(
                destination.stat().st_mtime,
                tz=UTC,
            )
            >= fresh_after
        ):
            return False
        temporary = destination.with_suffix(f"{destination.suffix}.part")
        async with client.stream("GET", f"{IMDB_DATASETS}/{filename}") as response:
            response.raise_for_status()
            with temporary.open("wb") as handle:
                async for chunk in response.aiter_bytes(1024 * 1024):
                    handle.write(chunk)
        temporary.replace(destination)
        return True

    @staticmethod
    def _matching_rows(
        path: Path,
        id_column: str,
        wanted: set[str],
        *,
        multiple: bool = False,
    ) -> dict[str, Any]:
        output: dict[str, Any] = {}
        if not wanted:
            return output
        with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
            reader = _tsv_reader(handle)
            for row in reader:
                identity = row.get(id_column)
                if identity not in wanted:
                    continue
                if multiple:
                    output.setdefault(str(identity), []).append(dict(row))
                else:
                    output[str(identity)] = dict(row)
        return output

    @staticmethod
    def _enrich_movie(movie: Movie, row: dict[str, str | None]) -> None:
        primary_title = _value(row.get("primaryTitle"))
        original_title = _value(row.get("originalTitle"))
        runtime = _integer(row.get("runtimeMinutes"))
        genres = [
            item for item in str(row.get("genres") or "").split(",") if item and item != r"\N"
        ]
        if primary_title and movie.primary_source == "research_corpus":
            movie.title = primary_title
        movie.original_title = original_title or movie.original_title
        movie.runtime_minutes = runtime or movie.runtime_minutes
        if genres and not json.loads(movie.genres_json or "[]"):
            movie.genres_json = json.dumps(genres)

    def _credits(
        self,
        movie: Movie,
        crew: dict[str, str | None],
        principals: list[dict[str, str | None]],
        people: dict[str, dict[str, str | None]],
    ) -> int:
        candidates: list[tuple[str, str, str, int | None, str]] = []
        candidates.extend(
            (identity, "Directing", "Director", None, "")
            for identity in _ids(crew.get("directors"))
        )
        candidates.extend(
            (identity, "Writing", "Writer", None, "") for identity in _ids(crew.get("writers"))
        )
        categories = {
            "actor": ("Acting", "Actor"),
            "actress": ("Acting", "Actor"),
            "self": ("Acting", "Actor"),
            "producer": ("Production", "Producer"),
            "writer": ("Writing", "Writer"),
            "director": ("Directing", "Director"),
        }
        for principal in principals:
            category = str(principal.get("category") or "")
            mapped = categories.get(category)
            identity = _value(principal.get("nconst"))
            if not mapped or not identity:
                continue
            candidates.append(
                (
                    identity,
                    mapped[0],
                    mapped[1],
                    _integer(principal.get("ordering")),
                    _first_character(principal.get("characters")),
                )
            )

        added = 0
        seen: set[tuple[str, str]] = set()
        for identity, department, job, order, character in candidates:
            key = (identity, job)
            if key in seen:
                continue
            seen.add(key)
            person_row = people.get(identity)
            if not person_row:
                continue
            name = _value(person_row.get("primaryName"))
            if not name:
                continue
            if self._credit_exists_by_name(movie, name, job):
                continue
            person = self.db.scalar(
                select(Person).where(
                    Person.source == "imdb",
                    Person.source_id == identity,
                )
            )
            if person is None:
                person = Person(
                    name=name,
                    source="imdb",
                    source_id=identity,
                    profile_url=f"https://www.imdb.com/name/{identity}/",
                )
                self.db.add(person)
                self.db.flush()
            self.db.add(
                Credit(
                    movie_id=movie.id,
                    person_id=person.id,
                    department=department,
                    job=job,
                    character_name=character,
                    billing_order=order,
                )
            )
            added += 1
        return added

    def _credit_exists_by_name(self, movie: Movie, name: str, job: str) -> bool:
        return (
            self.db.scalar(
                select(Credit.id)
                .join(Person, Credit.person_id == Person.id)
                .where(
                    Credit.movie_id == movie.id,
                    func.lower(Person.name) == name.casefold(),
                    Credit.job == job,
                )
                .limit(1)
            )
            is not None
        )


def _tsv_reader(handle: TextIO) -> csv.DictReader[str]:
    return csv.DictReader(
        handle,
        delimiter="\t",
        quoting=csv.QUOTE_NONE,
    )


def _value(value: str | None) -> str | None:
    return value if value and value != r"\N" else None


def _integer(value: str | None) -> int | None:
    normalized = _value(value)
    try:
        return int(normalized) if normalized else None
    except ValueError:
        return None


def _ids(value: str | None) -> list[str]:
    normalized = _value(value)
    return normalized.split(",") if normalized else []


def _first_character(value: str | None) -> str:
    normalized = _value(value)
    if not normalized:
        return ""
    try:
        parsed = json.loads(normalized)
    except json.JSONDecodeError:
        return ""
    return str(parsed[0]) if isinstance(parsed, list) and parsed else ""
