from __future__ import annotations

import hashlib
import json
import math
import pickle
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from slatesignal.modeling.encoder import BertMeanPoolEncoder
from slatesignal.modeling.features import (
    FEATURE_NAMES,
    STRUCTURED_FEATURES,
    DirectorHistory,
    full_feature_vector,
    structured_vector,
)


@dataclass(frozen=True)
class BaselinePrediction:
    p10: float
    p50: float
    p90: float
    log_prediction: float
    feature_vector_hash: str
    contributions: dict[str, float]
    encoder_mode: str


class ResearchBaselinePredictor:
    """Deployable implementation of the original notebook BERT+XGBoost model."""

    def __init__(
        self,
        *,
        artifact_path: str | Path,
        manifest_path: str | Path,
        encoder: BertMeanPoolEncoder,
    ) -> None:
        self.artifact_path = Path(artifact_path)
        self.manifest_path = Path(manifest_path)
        self.encoder = encoder
        self._model: Any = None
        self._manifest: dict[str, Any] | None = None

    @property
    def available(self) -> bool:
        return self.artifact_path.exists()

    @property
    def manifest(self) -> dict[str, Any]:
        if self._manifest is None:
            self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return self._manifest

    def predict(
        self,
        *,
        text: str,
        budget: float,
        release_year: int,
        director_history: DirectorHistory | None,
        genres: Sequence[str],
        embedding: np.ndarray | None = None,
    ) -> BaselinePrediction:
        if not self.available:
            raise FileNotFoundError(f"Missing model artifact: {self.artifact_path}")
        history = director_history
        if history is None:
            history = DirectorHistory(
                films=0,
                average_revenue=float(
                    self.manifest.get(
                        "director_history_fallback_revenue",
                        50_000_000.0,
                    )
                ),
                maximum_revenue=0.0,
            )
        structured = structured_vector(
            budget=budget,
            release_year=release_year,
            director_history=history,
            genres=genres,
        )
        bert_embedding = embedding if embedding is not None else self.encoder.encode(text)
        vector = full_feature_vector(structured, bert_embedding)
        model = self._load_model()
        log_prediction = float(model.predict(vector)[0])
        p50 = max(0.0, float(np.expm1(log_prediction)))
        q = self._conformal_radius(budget)
        p10 = max(0.0, float(np.expm1(log_prediction - q)))
        p90 = max(p50, float(np.expm1(log_prediction + q)))
        return BaselinePrediction(
            p10=p10,
            p50=p50,
            p90=p90,
            log_prediction=log_prediction,
            feature_vector_hash=hashlib.sha256(vector.tobytes()).hexdigest(),
            contributions=self._contributions(model, vector, p50),
            encoder_mode=self.encoder.mode,
        )

    def _load_model(self) -> Any:
        if self._model is None:
            if self.artifact_path.suffix in {".ubj", ".json"}:
                import xgboost as xgb

                self._model = xgb.XGBRegressor()
                self._model.load_model(self.artifact_path)
            else:
                with self.artifact_path.open("rb") as handle:
                    self._model = pickle.load(handle)  # noqa: S301 - trusted local artifact
            if int(getattr(self._model, "n_features_in_", 783)) != 783:
                raise ValueError("Model artifact does not match the 783-feature contract")
        return self._model

    def _conformal_radius(self, budget: float) -> float:
        segment = (
            "micro"
            if budget < 5_000_000
            else "low"
            if budget < 20_000_000
            else "mid"
            if budget < 80_000_000
            else "high"
            if budget < 180_000_000
            else "blockbuster"
        )
        radii = self.manifest.get("conformal_log_radius", {})
        value = radii.get(segment, radii.get("global", 1.15))
        return max(0.05, float(value))

    @staticmethod
    def _contributions(model: Any, vector: np.ndarray, p50: float) -> dict[str, float]:
        try:
            import xgboost as xgb

            contribution_values = model.get_booster().predict(
                xgb.DMatrix(vector, feature_names=list(FEATURE_NAMES)),
                pred_contribs=True,
            )[0]
        except (AttributeError, ValueError):
            return {}

        output = {
            name: p50 * math.expm1(float(value))
            for name, value in zip(STRUCTURED_FEATURES, contribution_values[:15], strict=True)
        }
        embedding_log_impact = float(np.sum(contribution_values[15:783]))
        output["synopsis_embedding"] = p50 * math.expm1(embedding_log_impact)
        return output
