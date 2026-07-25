"""Export and quantize the exact mean-pooled BERT encoder used by bert-xgb-v1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
import xgboost as xgb
from onnxruntime.transformers.float16 import convert_float_to_float16
from transformers import AutoModel, AutoTokenizer

from slatesignal.modeling.features import full_feature_vector, structured_vector


class LastHiddenState(torch.nn.Module):
    def __init__(self, model: torch.nn.Module) -> None:
        super().__init__()
        self.model = model

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
    ) -> torch.Tensor:
        return self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        ).last_hidden_state


def mean_pool(hidden: np.ndarray, mask: np.ndarray) -> np.ndarray:
    expanded = np.expand_dims(mask.astype(np.float32), axis=-1)
    return (hidden * expanded).sum(axis=1) / np.clip(expanded.sum(axis=1), 1, None)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="bert-base-uncased")
    parser.add_argument(
        "--output",
        default="services/inference/artifacts/bert-base-uncased-fp16.onnx",
    )
    parser.add_argument(
        "--tokenizer-output",
        default="services/inference/artifacts/bert-tokenizer",
    )
    parser.add_argument(
        "--xgboost-model",
        default="services/inference/artifacts/bert-xgb-v1.ubj",
    )
    parser.add_argument("--keep-fp32", action="store_true")
    args = parser.parse_args()

    output = Path(args.output).resolve()
    tokenizer_output = Path(args.tokenizer_output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer_output.mkdir(parents=True, exist_ok=True)
    float_output = output.with_name(f"{output.stem.removesuffix('-int8')}-fp32.onnx")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    model = AutoModel.from_pretrained(
        args.model,
        local_files_only=True,
        attn_implementation="eager",
    )
    model.eval()
    tokenizer.save_pretrained(tokenizer_output)
    encoded = tokenizer(
        "A test synopsis for SlateSignal model parity.",
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=512,
    )
    wrapper = LastHiddenState(model)
    torch.onnx.export(
        wrapper,
        (
            encoded["input_ids"],
            encoded["attention_mask"],
            encoded["token_type_ids"],
        ),
        float_output,
        input_names=["input_ids", "attention_mask", "token_type_ids"],
        output_names=["last_hidden_state"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "sequence"},
            "attention_mask": {0: "batch", 1: "sequence"},
            "token_type_ids": {0: "batch", 1: "sequence"},
            "last_hidden_state": {0: "batch", 1: "sequence"},
        },
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )
    # torch.onnx.export may restore the wrapper's training state recursively.
    model.eval()
    fp16_model = convert_float_to_float16(
        onnx.load(float_output),
        keep_io_types=True,
        disable_shape_infer=False,
    )
    onnx.save(fp16_model, output)

    samples = [
        "A family drama unfolds during a winter holiday.",
        "A stranded astronaut hears a signal from Earth.",
        "Peter Parker faces a threat that nobody else can see.",
    ]
    max_deltas = []
    cosine_similarities = []
    root_mean_squared_errors = []
    prediction_deltas = []
    prediction_relative_deltas = []
    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    revenue_model = xgb.XGBRegressor()
    revenue_model.load_model(Path(args.xgboost_model))
    structured = structured_vector(
        budget=50_000_000,
        release_year=2026,
        director_history=None,
        genres=["Drama"],
    )
    for sample in samples:
        tokens_pt = tokenizer(
            sample,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=512,
        )
        with torch.inference_mode():
            expected_hidden = model(**tokens_pt).last_hidden_state.numpy()
        tokens_np = {key: value.numpy().astype(np.int64) for key, value in tokens_pt.items()}
        actual_hidden = session.run(None, tokens_np)[0]
        expected = mean_pool(expected_hidden, tokens_np["attention_mask"])
        actual = mean_pool(actual_hidden, tokens_np["attention_mask"])
        difference = expected - actual
        max_deltas.append(float(np.max(np.abs(difference))))
        root_mean_squared_errors.append(float(np.sqrt(np.mean(np.square(difference)))))
        cosine_similarities.append(
            float(
                np.dot(expected[0], actual[0])
                / (np.linalg.norm(expected[0]) * np.linalg.norm(actual[0]))
            )
        )
        expected_revenue = float(
            np.expm1(revenue_model.predict(full_feature_vector(structured, expected[0]))[0])
        )
        actual_revenue = float(
            np.expm1(revenue_model.predict(full_feature_vector(structured, actual[0]))[0])
        )
        prediction_delta = abs(actual_revenue - expected_revenue)
        prediction_deltas.append(prediction_delta)
        prediction_relative_deltas.append(prediction_delta / max(1.0, expected_revenue))
    digest = hashlib.sha256()
    with output.open("rb") as handle:
        while block := handle.read(1024 * 1024):
            digest.update(block)
    try:
        portable_path = str(output.relative_to(Path.cwd()))
    except ValueError:
        portable_path = output.name
    report = {
        "model": args.model,
        "pooling": "attention-mask-aware mean pooling",
        "max_length": 512,
        "samples": len(samples),
        "max_absolute_embedding_delta": max(max_deltas),
        "max_embedding_rmse": max(root_mean_squared_errors),
        "min_embedding_cosine_similarity": min(cosine_similarities),
        "max_downstream_prediction_delta_usd": max(prediction_deltas),
        "max_downstream_prediction_relative_delta": max(prediction_relative_deltas),
        "onnx_path": portable_path,
        "onnx_sha256": digest.hexdigest(),
        "quantization": "float16 weights and activations with float32 I/O",
    }
    output.with_suffix(".parity.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not args.keep_fp32:
        float_output.unlink(missing_ok=True)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
