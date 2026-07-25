from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.core.config import Settings, get_settings
from slatesignal.domain.models import (
    ActualGross,
    Company,
    Credit,
    ExternalIdentifier,
    Movie,
    MovieCompany,
    Person,
    Release,
)
from slatesignal.services.provenance import payload_checksum, record_observation

TMDB_API = "https://api.themoviedb.org/3"
TMDB_IMAGE = "https://image.tmdb.org/t/p"
US_THEATRICAL_TYPES = {2: "limited", 3: "wide"}


class MissingTmdbToken(RuntimeError):
    pass


class TmdbCatalogSync:
    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        if not self.settings.tmdb_api_token:
            raise MissingTmdbToken(
                "TMDB_API_TOKEN is required for the exhaustive theatrical catalog sync"
            )
        self.headers = {
            "Authorization": f"Bearer {self.settings.tmdb_api_token}",
            "accept": "application/json",
        }

    async def sync(
        self,
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, int]:
        start = start or self.settings.catalog_start_date
        end = end or self.settings.catalog_end_date
        stats = {"discovered": 0, "enriched": 0, "created": 0, "updated": 0}
        seen: set[int] = set()
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=self.settings.request_timeout_seconds,
        ) as client:
            async for summary in self._discover(client, start=start, end=end):
                tmdb_id = int(summary["id"])
                if tmdb_id in seen:
                    continue
                seen.add(tmdb_id)
                stats["discovered"] += 1
                details = await self._get_json(
                    client,
                    f"/movie/{tmdb_id}",
                    params={
                        "language": "en-US",
                        "append_to_response": ("credits,release_dates,images,external_ids,videos"),
                        "include_image_language": "en,null",
                    },
                )
                created = self._upsert(details)
                stats["created" if created else "updated"] += 1
                stats["enriched"] += 1
                if stats["enriched"] % 50 == 0:
                    self.db.commit()
            self.db.commit()
        return stats

    async def _discover(
        self,
        client: httpx.AsyncClient,
        *,
        start: date,
        end: date,
    ) -> AsyncIterator[dict[str, Any]]:
        window_start = start
        while window_start <= end:
            window_end = min(end, window_start + timedelta(days=30))
            first = await self._get_json(
                client,
                "/discover/movie",
                params=self._discover_params(window_start, window_end, 1),
            )
            total_pages = min(int(first.get("total_pages", 1)), 500)
            for item in first.get("results", []):
                yield item
            for page in range(2, total_pages + 1):
                payload = await self._get_json(
                    client,
                    "/discover/movie",
                    params=self._discover_params(window_start, window_end, page),
                )
                for item in payload.get("results", []):
                    yield item
            window_start = window_end + timedelta(days=1)

    @staticmethod
    def _discover_params(
        start: date,
        end: date,
        page: int,
    ) -> dict[str, str | int | float | bool | None]:
        return {
            "region": "US",
            "with_release_type": "2|3",
            "release_date.gte": start.isoformat(),
            "release_date.lte": end.isoformat(),
            "include_adult": "false",
            "include_video": "false",
            "language": "en-US",
            "sort_by": "primary_release_date.asc",
            "page": page,
        }

    async def _get_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, str | int | float | bool | None],
    ) -> dict[str, Any]:
        for attempt in range(5):
            response = await client.get(f"{TMDB_API}{path}", params=params)
            if response.status_code == 429:
                delay = float(response.headers.get("Retry-After", 1 + attempt))
                await asyncio.sleep(min(delay, 10))
                continue
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError(f"TMDB returned a non-object payload for {path}")
            return cast(dict[str, Any], payload)
        raise RuntimeError(f"TMDB rate limit persisted for {path}")

    def _upsert(self, details: dict[str, Any]) -> bool:
        observed_at = datetime.now(UTC)
        tmdb_id = str(details["id"])
        external = self.db.scalar(
            select(ExternalIdentifier).where(
                ExternalIdentifier.source == "tmdb",
                ExternalIdentifier.external_id == tmdb_id,
            )
        )
        us_releases = _us_releases(details)
        release_date = min((item[0] for item in us_releases), default=None)
        year = (
            release_date.year
            if release_date
            else _year(details.get("release_date")) or self.settings.catalog_end_date.year
        )
        movie = self.db.get(Movie, external.movie_id) if external else None
        created = movie is None
        if movie is None:
            movie = Movie(
                slug=_slug(details.get("title") or details["original_title"], year, tmdb_id),
                title=details.get("title") or details["original_title"],
                original_title=details.get("original_title"),
                synopsis=details.get("overview") or None,
                release_status=_release_status(release_date),
                release_date=release_date,
                release_year=year,
                date_precision="day" if release_date else "year",
                runtime_minutes=details.get("runtime") or None,
                certification=_certification(us_releases),
                original_language=details.get("original_language"),
                origin_country=(details.get("origin_country") or [None])[0],
                genres_json=json.dumps([item["name"] for item in details.get("genres", [])]),
                budget=float(details["budget"]) if details.get("budget") else None,
                budget_status="reported" if details.get("budget") else "unavailable",
                poster_url=_image(details.get("poster_path"), "w780"),
                backdrop_url=_image(details.get("backdrop_path"), "w1280"),
                trailer_url=_trailer(details),
                homepage_url=details.get("homepage") or None,
                primary_source="tmdb",
                source_confidence=0.88,
                data_updated_at=observed_at,
            )
            self.db.add(movie)
            self.db.flush()
        else:
            movie.title = details.get("title") or movie.title
            movie.original_title = details.get("original_title") or movie.original_title
            movie.synopsis = details.get("overview") or movie.synopsis
            movie.release_status = _release_status(release_date)
            movie.release_date = release_date
            movie.release_year = year
            movie.date_precision = "day" if release_date else "year"
            movie.runtime_minutes = details.get("runtime") or movie.runtime_minutes
            movie.certification = _certification(us_releases) or movie.certification
            movie.genres_json = json.dumps([item["name"] for item in details.get("genres", [])])
            if details.get("budget"):
                movie.budget = float(details["budget"])
                movie.budget_status = "reported"
            movie.poster_url = _image(details.get("poster_path"), "w780")
            movie.backdrop_url = _image(details.get("backdrop_path"), "w1280")
            movie.trailer_url = _trailer(details) or movie.trailer_url
            movie.homepage_url = details.get("homepage") or movie.homepage_url
            movie.primary_source = "tmdb"
            movie.source_confidence = max(movie.source_confidence, 0.88)
            movie.data_updated_at = observed_at

        observation = record_observation(
            self.db,
            movie_id=movie.id,
            source="tmdb",
            observation_type="movie_details",
            observed_at=observed_at,
            source_url=f"https://www.themoviedb.org/movie/{tmdb_id}",
            confidence=0.88,
            payload=details,
        )
        self._external_id(
            movie,
            "tmdb",
            tmdb_id,
            f"https://www.themoviedb.org/movie/{tmdb_id}",
        )
        imdb_id = details.get("external_ids", {}).get("imdb_id")
        if imdb_id:
            self._external_id(
                movie,
                "imdb",
                imdb_id,
                f"https://www.imdb.com/title/{imdb_id}/",
            )
        self._credits(movie, details.get("credits", {}))
        self._companies(movie, details.get("production_companies", []))
        self._releases(movie, us_releases, observation.id)
        self._actual(movie, details, observed_at)
        return created

    def _external_id(
        self,
        movie: Movie,
        source: str,
        external_id: str,
        source_url: str,
    ) -> None:
        exists = self.db.scalar(
            select(ExternalIdentifier).where(
                ExternalIdentifier.source == source,
                ExternalIdentifier.external_id == external_id,
            )
        )
        if exists is None:
            self.db.add(
                ExternalIdentifier(
                    movie_id=movie.id,
                    source=source,
                    external_id=external_id,
                    source_url=source_url,
                )
            )

    def _credits(self, movie: Movie, payload: dict[str, Any]) -> None:
        raw_credits: list[tuple[dict[str, Any], str, str, str, int | None]] = []
        raw_credits.extend(
            (item, "Acting", "Actor", item.get("character") or "", item.get("order"))
            for item in payload.get("cast", [])[:20]
        )
        raw_credits.extend(
            (
                item,
                item.get("department") or "Crew",
                item.get("job") or "",
                "",
                None,
            )
            for item in payload.get("crew", [])
            if item.get("job") in {"Director", "Writer", "Screenplay", "Producer"}
        )
        for item, department, job, character, billing_order in raw_credits:
            source_id = str(item["id"])
            person = self.db.scalar(
                select(Person).where(
                    Person.source == "tmdb",
                    Person.source_id == source_id,
                )
            )
            if person is None:
                person = Person(
                    name=item.get("name") or "Unknown",
                    source="tmdb",
                    source_id=source_id,
                    profile_url=f"https://www.themoviedb.org/person/{source_id}",
                    image_url=_image(item.get("profile_path"), "w342"),
                )
                self.db.add(person)
                self.db.flush()
            exists = self.db.scalar(
                select(Credit).where(
                    Credit.movie_id == movie.id,
                    Credit.person_id == person.id,
                    Credit.department == department,
                    Credit.job == job,
                    Credit.character_name == character,
                )
            )
            if exists is None:
                self.db.add(
                    Credit(
                        movie_id=movie.id,
                        person_id=person.id,
                        department=department,
                        job=job,
                        character_name=character,
                        billing_order=billing_order,
                    )
                )

    def _companies(self, movie: Movie, payload: list[dict[str, Any]]) -> None:
        for item in payload:
            source_id = str(item["id"])
            company = self.db.scalar(
                select(Company).where(
                    Company.source == "tmdb",
                    Company.source_id == source_id,
                )
            )
            if company is None:
                company = Company(
                    name=item["name"],
                    source="tmdb",
                    source_id=source_id,
                    logo_url=_image(item.get("logo_path"), "w342"),
                    origin_country=item.get("origin_country") or None,
                )
                self.db.add(company)
                self.db.flush()
            exists = self.db.scalar(
                select(MovieCompany).where(
                    MovieCompany.movie_id == movie.id,
                    MovieCompany.company_id == company.id,
                    MovieCompany.role == "production",
                )
            )
            if exists is None:
                self.db.add(
                    MovieCompany(
                        movie_id=movie.id,
                        company_id=company.id,
                        role="production",
                    )
                )

    def _releases(
        self,
        movie: Movie,
        releases: list[tuple[date, int, str | None, str | None]],
        observation_id: str,
    ) -> None:
        for release_date, release_type, certification, note in releases:
            label = US_THEATRICAL_TYPES[release_type]
            exists = self.db.scalar(
                select(Release).where(
                    Release.movie_id == movie.id,
                    Release.country_code == "US",
                    Release.release_type == label,
                    Release.release_date == release_date,
                )
            )
            if exists is None:
                self.db.add(
                    Release(
                        movie_id=movie.id,
                        country_code="US",
                        release_type=label,
                        release_date=release_date,
                        certification=certification,
                        note=note,
                        is_confirmed=True,
                        source_observation_id=observation_id,
                    )
                )

    def _actual(
        self,
        movie: Movie,
        details: dict[str, Any],
        observed_at: datetime,
    ) -> None:
        revenue = float(details.get("revenue") or 0)
        if revenue <= 0:
            return
        checksum = payload_checksum({"revenue": revenue})
        exists = self.db.scalar(
            select(ActualGross).where(
                ActualGross.movie_id == movie.id,
                ActualGross.target == "worldwide_total",
                ActualGross.source == "tmdb",
                ActualGross.raw_checksum == checksum,
            )
        )
        if exists is None:
            self.db.add(
                ActualGross(
                    movie_id=movie.id,
                    target="worldwide_total",
                    amount=revenue,
                    currency="USD",
                    amount_status=(
                        "final" if movie.release_status == "gross_closed" else "provisional"
                    ),
                    source="tmdb",
                    source_url=f"https://www.themoviedb.org/movie/{details['id']}",
                    confidence=0.72,
                    observed_at=observed_at,
                    raw_checksum=checksum,
                    conflict_group=f"{movie.id}:worldwide_total",
                )
            )


def _us_releases(
    details: dict[str, Any],
) -> list[tuple[date, int, str | None, str | None]]:
    countries = details.get("release_dates", {}).get("results", [])
    us = next((item for item in countries if item.get("iso_3166_1") == "US"), None)
    output = []
    for item in (us or {}).get("release_dates", []):
        release_type = int(item.get("type") or 0)
        if release_type not in US_THEATRICAL_TYPES:
            continue
        raw_date = str(item.get("release_date") or "")[:10]
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError:
            continue
        output.append(
            (
                parsed,
                release_type,
                item.get("certification") or None,
                item.get("note") or None,
            )
        )
    return output


def _certification(
    releases: list[tuple[date, int, str | None, str | None]],
) -> str | None:
    return next((item[2] for item in releases if item[2]), None)


def _release_status(release_date: date | None) -> str:
    if release_date is None:
        return "year_only"
    today = datetime.now(UTC).date()
    if release_date > today:
        return "confirmed"
    if release_date + timedelta(days=56) >= today:
        return "in_theaters"
    if release_date + timedelta(days=180) >= today:
        return "released"
    return "gross_closed"


def _trailer(details: dict[str, Any]) -> str | None:
    videos = details.get("videos", {}).get("results", [])
    candidates = [
        item
        for item in videos
        if item.get("site") == "YouTube"
        and item.get("official")
        and item.get("type") in {"Trailer", "Teaser"}
    ]
    candidates.sort(key=lambda item: (item.get("type") != "Trailer", item.get("published_at", "")))
    return f"https://www.youtube.com/watch?v={candidates[0]['key']}" if candidates else None


def _image(path: str | None, size: str) -> str | None:
    return f"{TMDB_IMAGE}/{size}{path}" if path else None


def _year(raw_date: str | None) -> int | None:
    try:
        return date.fromisoformat(raw_date or "").year
    except ValueError:
        return None


def _slug(title: str, year: int, tmdb_id: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", title.casefold()).strip("-")
    return f"{normalized}-{year}-{tmdb_id}"
