from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


class BertMeanPoolEncoder:
    """Mean-pooled bert-base-uncased encoder with ONNX-first CPU inference."""

    def __init__(
        self,
        *,
        model_name: str,
        onnx_path: str | Path,
        tokenizer_path: str | Path,
    ) -> None:
        self.model_name = model_name
        self.onnx_path = Path(onnx_path)
        self.tokenizer_path = Path(tokenizer_path)
        self._tokenizer: Any = None
        self._session: Any = None
        self._torch_model: Any = None

    @property
    def mode(self) -> str:
        return "onnx" if self.onnx_path.exists() else "transformers"

    def encode(self, text: str) -> np.ndarray:
        normalized = text.strip()
        if not normalized:
            raise ValueError("BERT input cannot be empty")
        if self.onnx_path.exists():
            return self._encode_onnx(normalized)
        return self._encode_transformers(normalized)

    def _load_tokenizer(self) -> Any:
        if self._tokenizer is None:
            if self.onnx_path.exists():
                from tokenizers import Tokenizer  # type: ignore[import-untyped]

                tokenizer_file = (
                    self.tokenizer_path / "tokenizer.json"
                    if self.tokenizer_path.is_dir()
                    else self.tokenizer_path
                )
                if not tokenizer_file.exists():
                    raise FileNotFoundError(f"Local tokenizer artifact not found: {tokenizer_file}")
                tokenizer = Tokenizer.from_file(str(tokenizer_file))
                tokenizer.enable_truncation(max_length=512)
                tokenizer.enable_padding(
                    length=512,
                    pad_id=0,
                    pad_type_id=0,
                    pad_token="[PAD]",  # noqa: S106 - tokenizer sentinel, not a credential
                )
                self._tokenizer = tokenizer
            else:
                from transformers import AutoTokenizer  # type: ignore[import-not-found]

                source = self.tokenizer_path if self.tokenizer_path.exists() else self.model_name
                self._tokenizer = AutoTokenizer.from_pretrained(source)
        return self._tokenizer

    def _encode_onnx(self, text: str) -> np.ndarray:
        if self._session is None:
            import onnxruntime as ort  # type: ignore[import-untyped]

            self._session = ort.InferenceSession(
                str(self.onnx_path),
                providers=["CPUExecutionProvider"],
            )
        tokenizer = self._load_tokenizer()
        encoded = tokenizer.encode(text)
        candidates = {
            "input_ids": np.asarray([encoded.ids], dtype=np.int64),
            "attention_mask": np.asarray([encoded.attention_mask], dtype=np.int64),
            "token_type_ids": np.asarray([encoded.type_ids], dtype=np.int64),
        }
        input_names = {item.name for item in self._session.get_inputs()}
        inputs = {key: value for key, value in candidates.items() if key in input_names}
        last_hidden_state = self._session.run(None, inputs)[0]
        return _mean_pool(last_hidden_state, inputs["attention_mask"])

    def _encode_transformers(self, text: str) -> np.ndarray:
        import torch
        from transformers import AutoModel

        tokenizer = self._load_tokenizer()
        if self._torch_model is None:
            self._torch_model = AutoModel.from_pretrained(self.model_name)
            self._torch_model.eval()
        encoded = tokenizer(
            text,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=512,
        )
        with torch.inference_mode():
            output = self._torch_model(**encoded).last_hidden_state
        return _mean_pool(
            output.detach().cpu().numpy(),
            encoded["attention_mask"].detach().cpu().numpy(),
        )


def _mean_pool(last_hidden_state: np.ndarray, attention_mask: np.ndarray) -> np.ndarray:
    mask = np.expand_dims(attention_mask.astype(np.float32), axis=-1)
    denominator = np.clip(mask.sum(axis=1), 1.0, None)
    pooled = (last_hidden_state.astype(np.float32) * mask).sum(axis=1) / denominator
    vector = pooled[0]
    if vector.shape != (768,):
        raise ValueError(f"Expected BERT hidden size 768, got {vector.shape}")
    return np.asarray(vector, dtype=np.float32)
