from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, date, datetime
from typing import Any

from slatesignal.core.database import Base, SessionLocal, engine
from slatesignal.domain.models import JobRun
from slatesignal.pipelines.actuals import ActualGrossReconciler
from slatesignal.pipelines.buzz import BuzzCollector
from slatesignal.pipelines.imdb import ImdbDatasetSync
from slatesignal.pipelines.tmdb import TmdbCatalogSync
from slatesignal.services.bootstrap import (
    bootstrap_historical_evaluations,
    bootstrap_holdout_evaluations,
    bootstrap_launch_forecasts,
    bootstrap_real_catalog,
)
from slatesignal.services.ledger import verify_ledger
from slatesignal.services.official_forecasts import snapshot_eligible_movies
from slatesignal.services.provenance import canonical_json


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="slatesignal")
    subcommands = root.add_subparsers(dest="command", required=True)
    subcommands.add_parser("seed", help="Load the source-backed local launch snapshot")

    catalog = subcommands.add_parser(
        "catalog-sync",
        help="Sync the exhaustive US theatrical catalog from TMDB",
    )
    catalog.add_argument("--start", type=date.fromisoformat)
    catalog.add_argument("--end", type=date.fromisoformat)

    imdb = subcommands.add_parser(
        "imdb-sync",
        help="Join the latest IMDb non-commercial dataset snapshots",
    )
    imdb.add_argument("--refresh", action="store_true")

    actuals = subcommands.add_parser(
        "actuals-sync",
        help="Reconcile actual grosses from Wikidata and Wikipedia",
    )
    actuals.add_argument("--limit", type=int, default=500)

    buzz = subcommands.add_parser(
        "buzz-sync",
        help="Collect pre-release Wikimedia, GDELT, YouTube, and Reddit signals",
    )
    buzz.add_argument("--limit", type=int, default=250)
    buzz.add_argument("--as-of", type=datetime.fromisoformat)

    forecast = subcommands.add_parser(
        "forecast-snapshot",
        help="Seal due T-180/T-90/T-30/T-7 forecasts",
    )
    forecast.add_argument("--force", action="store_true")
    forecast.add_argument("--cutoff", type=datetime.fromisoformat)
    subcommands.add_parser("verify-ledger", help="Verify the public forecast hash chain")
    return root


def _job_start(name: str) -> tuple[Any, JobRun]:
    db = SessionLocal()
    job = JobRun(
        job_name=name,
        status="running",
        started_at=datetime.now(UTC),
        cursor_json="{}",
        stats_json="{}",
    )
    db.add(job)
    db.commit()
    return db, job


def _job_finish(db: Any, job: JobRun, stats: dict[str, Any]) -> None:
    job.status = "succeeded"
    job.finished_at = datetime.now(UTC)
    job.stats_json = canonical_json(stats)
    db.commit()


def _job_fail(db: Any, job: JobRun, error: Exception) -> None:
    db.rollback()
    job = db.get(JobRun, job.id)
    if job:
        job.status = "failed"
        job.finished_at = datetime.now(UTC)
        job.error_text = str(error)[:4000]
        db.commit()


def main() -> None:
    args = parser().parse_args()
    Base.metadata.create_all(bind=engine)
    db, job = _job_start(args.command)
    try:
        if args.command == "seed":
            stats = {
                "catalog_created": bootstrap_real_catalog(db),
                "launch_forecasts_created": bootstrap_launch_forecasts(db),
                "historical_evaluations_created": bootstrap_historical_evaluations(db),
                "holdout_evaluations_created": bootstrap_holdout_evaluations(db),
            }
        elif args.command == "catalog-sync":
            stats = asyncio.run(TmdbCatalogSync(db).sync(start=args.start, end=args.end))
        elif args.command == "imdb-sync":
            stats = asyncio.run(ImdbDatasetSync(db).sync(refresh=args.refresh))
        elif args.command == "actuals-sync":
            stats = asyncio.run(ActualGrossReconciler(db).sync(limit=args.limit))
        elif args.command == "buzz-sync":
            as_of = args.as_of
            if as_of and as_of.tzinfo is None:
                as_of = as_of.replace(tzinfo=UTC)
            stats = asyncio.run(BuzzCollector(db).sync(as_of=as_of, limit=args.limit))
        elif args.command == "forecast-snapshot":
            cutoff = args.cutoff
            if cutoff and cutoff.tzinfo is None:
                cutoff = cutoff.replace(tzinfo=UTC)
            stats = snapshot_eligible_movies(
                db,
                force=args.force,
                cutoff=cutoff,
            )
        elif args.command == "verify-ledger":
            valid, entries = verify_ledger(db)
            stats = {"valid": valid, "entries": entries}
            if not valid:
                raise RuntimeError("Forecast ledger verification failed")
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
        _job_finish(db, job, stats)
        print(json.dumps(stats, indent=2, sort_keys=True))
    except Exception as error:
        _job_fail(db, job, error)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
