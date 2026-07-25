from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from slatesignal.core.config import Settings, get_settings
from slatesignal.domain.models import ActualGross, ExternalIdentifier, Movie
from slatesignal.services.provenance import payload_checksum, record_observation

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_ENTITY = "https://www.wikidata.org/wiki/Special:EntityData"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USD_ENTITY = "Q4917"


class ActualGrossReconciler:
    """Append source-specific actuals while preserving conflicts and timestamps."""

    def __init__(self, db: Session, settings: Settings | None = None) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.headers = {
            "User-Agent": (
                "SlateSignal/0.2 (bias-aware film forecasting; "
                "research contact configured by deployer)"
            )
        }

    async def sync(self, *, limit: int = 500) -> dict[str, int]:
        movies = list(
            self.db.scalars(
                select(Movie)
                .options(selectinload(Movie.external_ids))
                .where(Movie.release_status.in_(["in_theaters", "released", "gross_closed"]))
                .order_by(Movie.release_date.desc())
                .limit(limit)
            ).unique()
        )
        imdb_to_movie = {
            external.external_id: movie
            for movie in movies
            for external in movie.external_ids
            if external.source == "imdb"
        }
        stats = {
            "eligible": len(movies),
            "with_imdb_id": len(imdb_to_movie),
            "wikidata_resolved": 0,
            "wikidata_actuals_added": 0,
            "wikipedia_actuals_added": 0,
            "wikipedia_unparsed": 0,
        }
        if not imdb_to_movie:
            return stats

        async with httpx.AsyncClient(
            timeout=self.settings.request_timeout_seconds,
            headers=self.headers,
            follow_redirects=True,
        ) as client:
            for imdb_batch in _batches(list(imdb_to_movie), 50):
                resolved = await self._resolve_wikidata(client, imdb_batch)
                for imdb_id, wikidata_id in resolved.items():
                    movie = imdb_to_movie[imdb_id]
                    stats["wikidata_resolved"] += 1
                    self._external_id(movie, wikidata_id)
                    entity = await self._entity(client, wikidata_id)
                    stats["wikidata_actuals_added"] += self._wikidata_actuals(
                        movie,
                        wikidata_id,
                        entity,
                    )
                    wikipedia_title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")
                    if not wikipedia_title:
                        continue
                    added, parsed = await self._wikipedia_actual(
                        client,
                        movie,
                        str(wikipedia_title),
                    )
                    stats["wikipedia_actuals_added"] += int(added)
                    stats["wikipedia_unparsed"] += int(not parsed)
                self.db.commit()
        return stats

    async def _resolve_wikidata(
        self,
        client: httpx.AsyncClient,
        imdb_ids: list[str],
    ) -> dict[str, str]:
        safe_ids = [item for item in imdb_ids if re.fullmatch(r"tt\d+", item)]
        values = " ".join(json.dumps(item) for item in safe_ids)
        query = f"SELECT ?film ?imdb WHERE {{ VALUES ?imdb {{ {values} }} ?film wdt:P345 ?imdb. }}"
        response = await client.get(
            WIKIDATA_SPARQL,
            params={"query": query, "format": "json"},
            headers={"Accept": "application/sparql-results+json", **self.headers},
        )
        response.raise_for_status()
        output: dict[str, str] = {}
        for binding in response.json().get("results", {}).get("bindings", []):
            imdb_id = binding.get("imdb", {}).get("value")
            entity_url = binding.get("film", {}).get("value")
            if imdb_id and entity_url:
                output[str(imdb_id)] = str(entity_url).rsplit("/", 1)[-1]
        return output

    async def _entity(
        self,
        client: httpx.AsyncClient,
        wikidata_id: str,
    ) -> dict[str, Any]:
        response = await client.get(f"{WIKIDATA_ENTITY}/{wikidata_id}.json")
        response.raise_for_status()
        return dict(response.json()["entities"][wikidata_id])

    def _external_id(self, movie: Movie, wikidata_id: str) -> None:
        exists = self.db.scalar(
            select(ExternalIdentifier).where(
                ExternalIdentifier.source == "wikidata",
                ExternalIdentifier.external_id == wikidata_id,
            )
        )
        if exists is None:
            self.db.add(
                ExternalIdentifier(
                    movie_id=movie.id,
                    source="wikidata",
                    external_id=wikidata_id,
                    source_url=f"https://www.wikidata.org/wiki/{wikidata_id}",
                )
            )

    def _wikidata_actuals(
        self,
        movie: Movie,
        wikidata_id: str,
        entity: dict[str, Any],
    ) -> int:
        observed_at = datetime.now(UTC)
        claims = entity.get("claims", {}).get("P2142", [])
        record_observation(
            self.db,
            movie_id=movie.id,
            source="wikidata",
            observation_type="worldwide_gross_claim",
            observed_at=observed_at,
            source_url=f"https://www.wikidata.org/wiki/{wikidata_id}#P2142",
            confidence=0.82,
            payload={"entity": wikidata_id, "claims": claims},
            forecast_eligible=False,
        )
        added = 0
        for claim in claims:
            value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            unit = str(value.get("unit", "")).rsplit("/", 1)[-1]
            if unit != USD_ENTITY:
                continue
            try:
                amount = float(value["amount"])
            except (KeyError, TypeError, ValueError):
                continue
            added += int(
                self._store_actual(
                    movie=movie,
                    amount=amount,
                    source="wikidata",
                    source_url=f"https://www.wikidata.org/wiki/{wikidata_id}#P2142",
                    confidence=0.82,
                    observed_at=observed_at,
                    raw_payload=claim,
                )
            )
        return added

    async def _wikipedia_actual(
        self,
        client: httpx.AsyncClient,
        movie: Movie,
        title: str,
    ) -> tuple[bool, bool]:
        response = await client.get(
            WIKIPEDIA_API,
            params={
                "action": "parse",
                "page": title,
                "prop": "wikitext",
                "format": "json",
                "formatversion": 2,
                "redirects": 1,
            },
        )
        response.raise_for_status()
        payload = response.json()
        observed_at = datetime.now(UTC)
        source_url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        record_observation(
            self.db,
            movie_id=movie.id,
            source="wikipedia",
            observation_type="infobox_gross_snapshot",
            observed_at=observed_at,
            source_url=source_url,
            confidence=0.76,
            payload=payload,
            forecast_eligible=False,
        )
        wikitext = payload.get("parse", {}).get("wikitext", "")
        amount = parse_wikipedia_usd_gross(str(wikitext))
        if amount is None:
            return False, False
        added = self._store_actual(
            movie=movie,
            amount=amount,
            source="wikipedia",
            source_url=source_url,
            confidence=0.76,
            observed_at=observed_at,
            raw_payload={"title": title, "gross_usd": amount},
        )
        return added, True

    def _store_actual(
        self,
        *,
        movie: Movie,
        amount: float,
        source: str,
        source_url: str,
        confidence: float,
        observed_at: datetime,
        raw_payload: Any,
    ) -> bool:
        checksum = payload_checksum(raw_payload)
        exists = self.db.scalar(
            select(ActualGross).where(
                ActualGross.movie_id == movie.id,
                ActualGross.target == "worldwide_total",
                ActualGross.source == source,
                ActualGross.raw_checksum == checksum,
            )
        )
        if exists is not None:
            return False
        self.db.add(
            ActualGross(
                movie_id=movie.id,
                target="worldwide_total",
                amount=amount,
                currency="USD",
                amount_status=(
                    "provisional"
                    if movie.release_status in {"in_theaters", "released"}
                    else "final"
                ),
                source=source,
                source_url=source_url,
                confidence=confidence,
                observed_at=observed_at,
                raw_checksum=checksum,
                conflict_group=f"{movie.id}:worldwide_total",
            )
        )
        return True


def parse_wikipedia_usd_gross(wikitext: str) -> float | None:
    match = re.search(
        r"(?ims)^\s*\|\s*gross\s*=\s*(.+?)(?=^\s*\||^\s*}}\s*$)",
        wikitext,
    )
    if not match:
        return None
    raw = re.sub(r"<ref\b[^>]*>.*?</ref>|<ref\b[^>]*/>", "", match.group(1))
    raw = re.sub(r"\{\{\s*US\$\s*\|\s*", "US$", raw, flags=re.IGNORECASE)
    raw = raw.replace("|million", " million").replace("|billion", " billion")
    if re.search(r"\$\s*[\d,.]+\s*[-–—]\s*[\d,.]+", raw):
        return None
    values = re.findall(
        r"(?:US\s*)?\$\s*([\d,.]+)\s*(thousand|million|billion)?",
        raw,
        flags=re.IGNORECASE,
    )
    if len(values) != 1:
        return None
    number, scale = values[0]
    try:
        amount = float(number.replace(",", ""))
    except ValueError:
        return None
    multiplier = {
        "": 1.0,
        "thousand": 1_000.0,
        "million": 1_000_000.0,
        "billion": 1_000_000_000.0,
    }[scale.casefold()]
    return amount * multiplier


def _batches(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]
