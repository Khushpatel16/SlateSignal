from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.core.config import Settings, get_settings
from slatesignal.domain.models import BuzzSnapshot, Movie
from slatesignal.services.provenance import (
    payload_checksum,
    record_observation,
)

WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
PAGEVIEWS_API = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user"
)
GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3/videos"
REDDIT_OAUTH_ENDPOINT = "https://www.reddit.com/api/v1/access_token"
REDDIT_SEARCH = "https://oauth.reddit.com/search"


@dataclass(frozen=True)
class BuzzMeasurement:
    source: str
    metric: str
    value: float
    normalized_value: float | None
    momentum: float | None
    source_url: str
    confidence: float
    payload: Any


class BuzzCollector:
    """Collect time-stamped demand signals without post-cutoff look-ahead."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.headers = {
            "User-Agent": (
                f"SlateSignal/0.2 (bias-aware film forecasting; {self.settings.reddit_user_agent})"
            )
        }

    async def sync(
        self,
        *,
        as_of: datetime | None = None,
        limit: int = 250,
    ) -> dict[str, int]:
        as_of = as_of or datetime.now(UTC)
        start = as_of.date() - timedelta(days=56)
        end = as_of.date() + timedelta(days=180)
        movies = list(
            self.db.scalars(
                select(Movie)
                .where(
                    Movie.release_date.is_not(None),
                    Movie.release_date >= start,
                    Movie.release_date <= end,
                    Movie.release_status.in_(["confirmed", "in_theaters"]),
                )
                .order_by(Movie.release_date.asc())
                .limit(limit)
            )
        )
        stats = {
            "eligible": len(movies),
            "snapshots_added": 0,
            "source_errors": 0,
            "google_trends_skipped": len(movies),
        }
        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            headers=self.headers,
            follow_redirects=True,
        ) as client:
            reddit_token = await self._reddit_token(client)
            for movie in movies:
                collectors = [
                    self._wikimedia(client, movie, as_of.date()),
                    self._gdelt(client, movie),
                ]
                if self.settings.youtube_api_key and movie.trailer_url:
                    collectors.append(self._youtube(client, movie))
                if reddit_token:
                    collectors.append(self._reddit(client, movie, reddit_token))
                for collector in collectors:
                    try:
                        measurement = await collector
                    except (httpx.HTTPError, KeyError, TypeError, ValueError):
                        stats["source_errors"] += 1
                        continue
                    if measurement and self._store(movie, measurement, as_of):
                        stats["snapshots_added"] += 1
                self.db.commit()
        return stats

    async def _wikimedia(
        self,
        client: httpx.AsyncClient,
        movie: Movie,
        as_of: date,
    ) -> BuzzMeasurement | None:
        search = await client.get(
            WIKIPEDIA_API,
            params={
                "action": "query",
                "list": "search",
                "srsearch": f'intitle:"{movie.title}" film {movie.release_year}',
                "srlimit": 3,
                "format": "json",
            },
        )
        search.raise_for_status()
        results = search.json().get("query", {}).get("search", [])
        if not results:
            return None
        title = str(results[0]["title"])
        end = as_of - timedelta(days=1)
        start = end - timedelta(days=27)
        encoded_title = quote(title.replace(" ", "_"), safe="")
        pageviews = await client.get(
            f"{PAGEVIEWS_API}/{encoded_title}/daily/{start:%Y%m%d}/{end:%Y%m%d}",
        )
        pageviews.raise_for_status()
        payload = {
            "search": search.json(),
            "pageviews": pageviews.json(),
            "resolved_title": title,
        }
        values = [float(item.get("views", 0)) for item in pageviews.json().get("items", [])]
        if not values:
            return None
        current = sum(values[-7:])
        previous = sum(values[-14:-7])
        return BuzzMeasurement(
            source="wikimedia",
            metric="pageviews_7d",
            value=current,
            normalized_value=_log_scale(current, ceiling=10_000_000),
            momentum=_growth(current, previous),
            source_url=f"https://en.wikipedia.org/wiki/{encoded_title}",
            confidence=0.88,
            payload=payload,
        )

    async def _gdelt(
        self,
        client: httpx.AsyncClient,
        movie: Movie,
    ) -> BuzzMeasurement | None:
        query = f'"{movie.title}" AND (film OR movie)'
        response = await client.get(
            GDELT_API,
            params={
                "query": query,
                "mode": "TimelineVolRaw",
                "format": "json",
                "timespan": "1month",
                "maxrecords": 250,
            },
        )
        response.raise_for_status()
        payload = response.json()
        values = _timeline_values(payload)
        if not values:
            return None
        current = sum(values[-7:])
        previous = sum(values[-14:-7])
        return BuzzMeasurement(
            source="gdelt",
            metric="news_mentions_7d",
            value=current,
            normalized_value=_log_scale(current, ceiling=10_000),
            momentum=_growth(current, previous),
            source_url=f"{GDELT_API}?query={quote(query)}",
            confidence=0.70,
            payload=payload,
        )

    async def _youtube(
        self,
        client: httpx.AsyncClient,
        movie: Movie,
    ) -> BuzzMeasurement | None:
        video_id = _youtube_id(movie.trailer_url)
        if not video_id or not self.settings.youtube_api_key:
            return None
        response = await client.get(
            YOUTUBE_API,
            params={
                "part": "statistics,snippet",
                "id": video_id,
                "key": self.settings.youtube_api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items", [])
        if not items:
            return None
        statistics = items[0].get("statistics", {})
        views = float(statistics.get("viewCount", 0))
        prior = self._prior_value(movie, "youtube", "trailer_views")
        return BuzzMeasurement(
            source="youtube",
            metric="trailer_views",
            value=views,
            normalized_value=_log_scale(views, ceiling=200_000_000),
            momentum=_growth(views, prior) if prior is not None else None,
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            confidence=0.92,
            payload=payload,
        )

    async def _reddit_token(self, client: httpx.AsyncClient) -> str | None:
        if not (self.settings.reddit_client_id and self.settings.reddit_client_secret):
            return None
        response = await client.post(
            REDDIT_OAUTH_ENDPOINT,
            data={"grant_type": "client_credentials"},
            auth=httpx.BasicAuth(
                self.settings.reddit_client_id,
                self.settings.reddit_client_secret,
            ),
            headers={"User-Agent": self.settings.reddit_user_agent},
        )
        response.raise_for_status()
        return str(response.json()["access_token"])

    async def _reddit(
        self,
        client: httpx.AsyncClient,
        movie: Movie,
        token: str,
    ) -> BuzzMeasurement | None:
        response = await client.get(
            REDDIT_SEARCH,
            params={
                "q": f'"{movie.title}"',
                "sort": "new",
                "t": "month",
                "limit": 100,
                "restrict_sr": "false",
            },
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.settings.reddit_user_agent,
            },
        )
        response.raise_for_status()
        payload = response.json()
        posts = payload.get("data", {}).get("children", [])
        attention = sum(
            max(0, float(item.get("data", {}).get("score", 0)))
            + max(0, float(item.get("data", {}).get("num_comments", 0)))
            for item in posts
        )
        return BuzzMeasurement(
            source="reddit",
            metric="community_attention_30d",
            value=attention,
            normalized_value=_log_scale(attention, ceiling=500_000),
            momentum=None,
            source_url=f"https://www.reddit.com/search/?q={quote(movie.title)}",
            confidence=0.66,
            payload=payload,
        )

    def _prior_value(
        self,
        movie: Movie,
        source: str,
        metric: str,
    ) -> float | None:
        prior = self.db.scalar(
            select(BuzzSnapshot)
            .where(
                BuzzSnapshot.movie_id == movie.id,
                BuzzSnapshot.source == source,
                BuzzSnapshot.metric == metric,
            )
            .order_by(BuzzSnapshot.observed_at.desc())
            .limit(1)
        )
        return prior.value if prior else None

    def _store(
        self,
        movie: Movie,
        measurement: BuzzMeasurement,
        observed_at: datetime,
    ) -> bool:
        checksum = payload_checksum(measurement.payload)
        exists = self.db.scalar(
            select(BuzzSnapshot).where(
                BuzzSnapshot.movie_id == movie.id,
                BuzzSnapshot.source == measurement.source,
                BuzzSnapshot.metric == measurement.metric,
                BuzzSnapshot.raw_checksum == checksum,
            )
        )
        if exists is not None:
            return False
        record_observation(
            self.db,
            movie_id=movie.id,
            source=measurement.source,
            observation_type=f"buzz_{measurement.metric}",
            observed_at=observed_at,
            source_url=measurement.source_url,
            confidence=measurement.confidence,
            payload=measurement.payload,
        )
        self.db.add(
            BuzzSnapshot(
                movie_id=movie.id,
                source=measurement.source,
                metric=measurement.metric,
                value=measurement.value,
                normalized_value=measurement.normalized_value,
                momentum=measurement.momentum,
                observed_at=observed_at,
                source_url=measurement.source_url,
                confidence=measurement.confidence,
                raw_checksum=checksum,
            )
        )
        return True


def _growth(current: float, previous: float) -> float:
    return (current - previous) / max(1.0, previous)


def _log_scale(value: float, *, ceiling: float) -> float:
    return min(100.0, max(0.0, math.log1p(value) / math.log1p(ceiling) * 100.0))


def _timeline_values(payload: Any) -> list[float]:
    timelines = payload.get("timeline", []) if isinstance(payload, dict) else []
    values: list[float] = []
    for timeline in timelines:
        for item in timeline.get("data", []):
            try:
                values.append(float(item.get("value", 0)))
            except (TypeError, ValueError):
                continue
    return values


def _youtube_id(url: str | None) -> str | None:
    if not url:
        return None
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return match.group(1) if match else None
