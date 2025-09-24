"""TextAttack-compatible wrapper around Hugging Face Inference API.

This allows attacking a remote model without downloading local weights.
The wrapper expects a text-classification endpoint that returns labels+scores.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import numpy as np
from textattack.models.wrappers import ModelWrapper
from huggingface_hub import InferenceClient


class HFInferenceAPIWrapper(ModelWrapper):
    def __init__(
        self,
        model_id: str,
        token: Optional[str] = None,
        labels: Optional[List[str]] = None,
        timeout: int = 30,
    ) -> None:
        self.model_id = model_id
        self.client = InferenceClient(token=token, timeout=timeout)
        # Label order used to build consistent logits vectors
        self.labels = labels  # type: Optional[List[str]]

    def _ensure_labels(self, res: List[dict]):
        if self.labels is None:
            # Infer stable order from first response
            self.labels = [d["label"] for d in res]

    def __call__(self, text_input_list: Iterable[str]):
        if isinstance(text_input_list, str):
            text_input_list = [text_input_list]

        logits_list = []
        for text in text_input_list:
            # The client returns list of {label, score} dicts for classification
            res = self.client.text_classification(text=text, model=self.model_id)
            self._ensure_labels(res)

            # Build probability vector in the established label order
            prob_map = {d["label"]: float(d["score"]) for d in res}
            probs = np.array([prob_map.get(lbl, 0.0) for lbl in self.labels], dtype=np.float32)

            # Numerical stability + convert to logits; for multi-class softmax, log probs suffice
            eps = 1e-12
            logits = np.log(np.clip(probs, eps, 1.0))
            logits_list.append(logits)

        return np.stack(logits_list, axis=0)

    def predict(self, texts: Iterable[str]) -> np.ndarray:
        logits = self(texts)
        return np.argmax(logits, axis=-1)

