from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from slatesignal.domain.models import ForecastRun, LedgerEntry
from slatesignal.services.provenance import canonical_json


def forecast_payload(forecast: ForecastRun) -> dict[str, object]:
    return {
        "forecast_id": forecast.id,
        "movie_id": forecast.movie_id,
        "model_version_id": forecast.model_version_id,
        "data_cutoff": _utc_isoformat(forecast.data_cutoff),
        "horizon_days": forecast.horizon_days,
        "forecast_type": forecast.forecast_type,
        "targets": forecast.targets_json,
        "factors": forecast.factors_json,
        "buzz": forecast.buzz_json,
        "comparables": forecast.comparables_json,
        "fairness": forecast.fairness_json,
        "evidence_manifest": forecast.evidence_manifest_json,
        "confidence_score": forecast.confidence_score,
        "feature_manifest_hash": forecast.feature_manifest_hash,
        "limitations": forecast.limitations_json,
        "generated_at": _utc_isoformat(forecast.generated_at),
    }


def _utc_isoformat(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat()


def seal_forecast(db: Session, forecast: ForecastRun) -> LedgerEntry:
    existing = db.scalar(select(LedgerEntry).where(LedgerEntry.forecast_run_id == forecast.id))
    if existing:
        return existing

    previous = db.scalar(select(LedgerEntry).order_by(LedgerEntry.sequence.desc()).limit(1))
    sequence = int(db.scalar(select(func.count(LedgerEntry.id))) or 0) + 1
    payload_hash = hashlib.sha256(
        canonical_json(forecast_payload(forecast)).encode("utf-8")
    ).hexdigest()
    previous_hash = previous.ledger_hash if previous else None
    ledger_hash = hashlib.sha256(
        f"{sequence}:{previous_hash or 'GENESIS'}:{payload_hash}".encode()
    ).hexdigest()
    entry = LedgerEntry(
        sequence=sequence,
        forecast_run_id=forecast.id,
        previous_hash=previous_hash,
        payload_hash=payload_hash,
        ledger_hash=ledger_hash,
        sealed_at=datetime.now(UTC),
    )
    db.add(entry)
    db.flush()
    return entry


def verify_ledger(db: Session) -> tuple[bool, int]:
    previous_hash: str | None = None
    count = 0
    for entry in db.scalars(select(LedgerEntry).order_by(LedgerEntry.sequence.asc())):
        forecast = db.get(ForecastRun, entry.forecast_run_id)
        if forecast is None:
            return False, count
        payload_hash = hashlib.sha256(
            canonical_json(forecast_payload(forecast)).encode("utf-8")
        ).hexdigest()
        expected = hashlib.sha256(
            f"{entry.sequence}:{previous_hash or 'GENESIS'}:{payload_hash}".encode()
        ).hexdigest()
        if (
            entry.payload_hash != payload_hash
            or entry.previous_hash != previous_hash
            or entry.ledger_hash != expected
        ):
            return False, count
        previous_hash = entry.ledger_hash
        count += 1
    return True, count
