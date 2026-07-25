from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from slatesignal.domain.models import SourceObservation


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def payload_checksum(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def record_observation(
    db: Session,
    *,
    movie_id: str | None,
    source: str,
    observation_type: str,
    observed_at: datetime,
    source_url: str,
    confidence: float,
    payload: Any,
    forecast_eligible: bool = True,
) -> SourceObservation:
    checksum = payload_checksum(payload)
    existing = db.scalar(
        select(SourceObservation).where(
            SourceObservation.movie_id == movie_id,
            SourceObservation.source == source,
            SourceObservation.observation_type == observation_type,
            SourceObservation.raw_checksum == checksum,
        )
    )
    if existing:
        return existing

    observation = SourceObservation(
        movie_id=movie_id,
        source=source,
        observation_type=observation_type,
        observed_at=observed_at,
        source_url=source_url,
        confidence=max(0.0, min(1.0, confidence)),
        raw_checksum=checksum,
        payload_json=canonical_json(payload),
        forecast_eligible=forecast_eligible,
    )
    db.add(observation)
    db.flush()
    return observation


def eligible_observations(
    db: Session,
    *,
    movie_id: str,
    cutoff: datetime,
) -> list[SourceObservation]:
    return list(
        db.scalars(
            select(SourceObservation)
            .where(
                SourceObservation.movie_id == movie_id,
                SourceObservation.forecast_eligible.is_(True),
                SourceObservation.observed_at <= cutoff,
            )
            .order_by(SourceObservation.observed_at.asc())
        )
    )
