import json
from datetime import UTC, date, datetime

from fastapi.testclient import TestClient

from slatesignal.core.database import SessionLocal
from slatesignal.domain.models import ForecastRun, Movie
from slatesignal.main import app
from slatesignal.services.ledger import verify_ledger
from slatesignal.services.provenance import record_observation


def _movie(slug: str) -> Movie:
    return Movie(
        slug=slug,
        title=slug.replace("-", " ").title(),
        original_title=None,
        synopsis="A source-provenance test record.",
        release_status="confirmed",
        release_date=date(2027, 5, 21),
        release_year=2027,
        date_precision="day",
        runtime_minutes=110,
        certification="PG-13",
        original_language="en",
        origin_country="US",
        genres_json='["Drama"]',
        budget=None,
        budget_status="unavailable",
        poster_url=None,
        backdrop_url=None,
        trailer_url=None,
        homepage_url=None,
        primary_source="test",
        source_confidence=0.9,
        data_updated_at=datetime(2026, 7, 24, tzinfo=UTC),
    )


def test_forecast_ledger_detects_any_post_seal_mutation() -> None:
    with TestClient(app):
        pass
    with SessionLocal() as db:
        valid, count = verify_ledger(db)
        assert valid is True
        assert count == 29

        forecast = db.query(ForecastRun).first()
        assert forecast is not None
        original = forecast.targets_json
        forecast.targets_json = json.dumps({"worldwide_total": None})
        db.flush()
        tamper_valid, checked = verify_ledger(db)
        forecast.targets_json = original
        db.rollback()

    assert tamper_valid is False
    assert checked < count


def test_every_sealed_evidence_timestamp_respects_its_cutoff() -> None:
    with TestClient(app):
        pass
    with SessionLocal() as db:
        forecasts = db.query(ForecastRun).all()
        assert forecasts
        for forecast in forecasts:
            cutoff = forecast.data_cutoff
            if cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=UTC)
            for evidence in json.loads(forecast.evidence_manifest_json):
                if "observed_at" not in evidence:
                    continue
                observed = datetime.fromisoformat(evidence["observed_at"])
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=UTC)
                assert observed <= cutoff


def test_observations_are_idempotent_per_movie_not_globally() -> None:
    with SessionLocal() as db:
        first_movie = _movie("first-source-test")
        second_movie = _movie("second-source-test")
        db.add_all([first_movie, second_movie])
        db.flush()
        kwargs = {
            "source": "source-test",
            "observation_type": "metadata",
            "observed_at": datetime(2026, 7, 24, tzinfo=UTC),
            "source_url": "https://example.com/source",
            "confidence": 0.8,
            "payload": {"same": "payload"},
        }
        first = record_observation(db, movie_id=first_movie.id, **kwargs)
        duplicate = record_observation(db, movie_id=first_movie.id, **kwargs)
        second = record_observation(db, movie_id=second_movie.id, **kwargs)

    assert duplicate.id == first.id
    assert second.id != first.id
