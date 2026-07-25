"""Fail CI when SlateSignal regresses to notebook, demo, or secret-backed behavior."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    ".next",
    ".venv",
    "__pycache__",
    "node_modules",
    "test-results",
}


def visible_files() -> list[Path]:
    return [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and not IGNORED_PARTS.intersection(path.parts)
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    files = visible_files()
    require(
        not [path for path in files if path.suffix == ".ipynb"],
        "Notebook files are forbidden in the production repository.",
    )
    require(
        not [
            path
            for path in files
            if path.suffix in {".pkl", ".pickle"} and "services/inference" in path.as_posix()
        ],
        "Pickle model artifacts are forbidden in the inference service.",
    )

    product_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in files
        if path.suffix in {".py", ".ts", ".tsx"}
        and ("apps/web/src" in path.as_posix() or "services/inference/src" in path.as_posix())
    ).casefold()
    for forbidden in (
        "curated_demo",
        "glass horizon",
        "solar divide",
        "hollow house",
    ):
        require(
            forbidden not in product_text,
            f"Forbidden fictional catalog residue found: {forbidden}",
        )

    text_files = [
        path
        for path in files
        if path.suffix in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".yaml", ".yml"}
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in text_files)
    require(
        re.search(r"AIza[0-9A-Za-z_-]{30,}", combined) is None,
        "A Google-style API key appears to be hardcoded.",
    )

    artifacts = ROOT / "services" / "inference" / "artifacts"
    baseline = json.loads((artifacts / "bert-xgb-v1.json").read_text())
    require(
        sha256(artifacts / "bert-xgb-v1.ubj") == baseline["model_sha256"],
        "bert-xgb-v1 artifact checksum does not match its manifest.",
    )
    require(
        baseline["feature_count"] == 783,
        "bert-xgb-v1 must preserve the exact 15 + 768 feature contract.",
    )
    tournament = json.loads((artifacts / "model-tournament-v2.json").read_text())
    require(
        tournament["promoted"] is False,
        "The corrected candidate cannot be promoted while a gate is failing.",
    )
    parity = json.loads((artifacts / "bert-base-uncased-fp16.parity.json").read_text())
    require(
        parity["min_embedding_cosine_similarity"] > 0.99999,
        "The quantized ONNX encoder failed its cosine-similarity gate.",
    )
    require(
        parity["max_downstream_prediction_relative_delta"] < 0.01,
        "The quantized ONNX encoder failed downstream prediction parity.",
    )

    seed = json.loads(
        (ROOT / "services" / "inference" / "data" / "real_film_seed.json").read_text()
    )
    launch = json.loads(
        (ROOT / "services" / "inference" / "data" / "launch_forecasts.json").read_text()
    )
    seed_slugs = {movie["slug"] for movie in seed["movies"]}
    launch_slugs = {item["movie"]["slug"] for item in launch["rows"]}
    require(len(launch_slugs) == 5, "The portable launch ledger must contain five films.")
    require(
        launch_slugs <= seed_slugs,
        "Every launch forecast must resolve to a source-backed catalog record.",
    )
    require(
        all(item["forecast_type"] == "official" for item in launch["rows"]),
        "Launch forecasts must be official ledger entries.",
    )
    historical = json.loads(
        (ROOT / "services" / "inference" / "data" / "historical_evaluations.json").read_text()
    )
    require(
        historical["is_ex_ante"] is False,
        "Retrospective temporal folds must never be labeled ex ante.",
    )
    require(
        len(historical["rows"]) == 480,
        "Historical evaluation coverage must include all 2021-2024 research rows.",
    )
    require(
        {int(item["release_year"]) for item in historical["rows"]} == {2021, 2022, 2023, 2024},
        "Historical evaluation years must remain 2021-2024.",
    )
    require(
        any(
            item["title"] == "Spider-Man: No Way Home"
            and item["model_version"] == "bert-xgb-temporal-2021"
            for item in historical["rows"]
        ),
        "The released-film prediction workflow lost its canonical 2021 fixture.",
    )
    for model in historical["model_versions"]:
        artifact_path = ROOT / model["artifact_uri"]
        require(
            artifact_path.exists() and sha256(artifact_path) == model["artifact_checksum"],
            f"Temporal-fold artifact checksum mismatch: {model['version']}",
        )
    print("Repository policy checks passed.")


if __name__ == "__main__":
    main()
