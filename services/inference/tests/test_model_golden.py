import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from slatesignal.modeling.encoder import BertMeanPoolEncoder
from slatesignal.modeling.features import DirectorHistory
from slatesignal.modeling.predictor import ResearchBaselinePredictor

SERVICE_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = SERVICE_ROOT / "artifacts"


def test_extracted_bert_xgb_model_matches_frozen_research_output() -> None:
    fixture = json.loads((ARTIFACTS / "golden-runtime-v1.json").read_text(encoding="utf-8"))
    history = fixture["input"]["director_history"]
    predictor = ResearchBaselinePredictor(
        artifact_path=ARTIFACTS / "bert-xgb-v1.ubj",
        manifest_path=ARTIFACTS / "bert-xgb-v1.json",
        encoder=BertMeanPoolEncoder(
            model_name="bert-base-uncased",
            onnx_path=ARTIFACTS / "not-required-for-frozen-embedding.onnx",
            tokenizer_path=ARTIFACTS / "bert-tokenizer",
        ),
    )
    prediction = predictor.predict(
        text=fixture["title"],
        budget=fixture["input"]["budget"],
        release_year=fixture["input"]["release_year"],
        director_history=(
            DirectorHistory(
                films=history["films"],
                average_revenue=history["avg_revenue"],
                maximum_revenue=history["max_revenue"],
            )
            if history
            else None
        ),
        genres=fixture["input"]["genres"],
        embedding=np.asarray(fixture["embedding"], dtype=np.float32),
    )

    assert prediction.feature_vector_hash == fixture["expected"]["feature_sha256"]
    assert prediction.log_prediction == pytest.approx(
        fixture["expected"]["prediction_log"],
        abs=1e-6,
    )
    assert prediction.p50 == pytest.approx(
        fixture["expected"]["prediction_usd"],
        rel=1e-6,
    )


def test_model_artifact_checksum_matches_version_manifest() -> None:
    manifest = json.loads((ARTIFACTS / "bert-xgb-v1.json").read_text(encoding="utf-8"))
    checksum = hashlib.sha256((ARTIFACTS / "bert-xgb-v1.ubj").read_bytes()).hexdigest()

    assert checksum == manifest["model_sha256"]
    assert manifest["feature_count"] == 783
    assert manifest["encoder"]["pooling"] == "attention-mask-aware mean pooling"


def test_quantized_onnx_encoder_passes_embedding_and_downstream_parity() -> None:
    parity = json.loads(
        (ARTIFACTS / "bert-base-uncased-fp16.parity.json").read_text(encoding="utf-8")
    )

    assert parity["min_embedding_cosine_similarity"] > 0.99999
    assert parity["max_embedding_rmse"] < 0.001
    assert parity["max_downstream_prediction_relative_delta"] < 0.01
    assert len(parity["onnx_sha256"]) == 64


def test_runtime_tokenizer_preserves_bert_input_ids(tmp_path: Path) -> None:
    onnx_path = tmp_path / "encoder.onnx"
    onnx_path.touch()
    encoder = BertMeanPoolEncoder(
        model_name="bert-base-uncased",
        onnx_path=onnx_path,
        tokenizer_path=ARTIFACTS / "bert-tokenizer",
    )

    encoded = encoder._load_tokenizer().encode(  # noqa: SLF001
        "A pilot crosses a hostile desert to protect a divided empire."
    )

    assert encoded.ids[:16] == [
        101,
        1037,
        4405,
        7821,
        1037,
        10420,
        5532,
        2000,
        4047,
        1037,
        4055,
        3400,
        1012,
        102,
        0,
        0,
    ]
    assert encoded.attention_mask[:16] == [1] * 14 + [0, 0]
