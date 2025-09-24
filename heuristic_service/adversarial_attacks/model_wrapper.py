"""Hugging Face sequence classification model wrapper compatible with TextAttack."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from textattack.models.wrappers import ModelWrapper


os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


class HFModelWrapper(ModelWrapper):
    """Load a local Hugging Face classifier and expose TextAttack-friendly APIs."""

    def __init__(
        self,
        model_path: str,
        device: str = "auto",
        max_length: int = 256,
        local_files_only: bool = True,
        trust_remote_code: bool = False,
        hf_token: Optional[str] = None,
    ) -> None:
        if device == "auto":
            target_device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            target_device = "cuda" if device == "cuda" and torch.cuda.is_available() else "cpu"

        self.device = target_device

        # Accept either a local directory or a Hugging Face Hub repo id
        src = model_path
        local_dir = Path(model_path).expanduser()
        is_local = local_dir.exists() and local_dir.is_dir()

        load_id = str(local_dir.resolve()) if is_local else src

        # When loading from hub, we must not force local files only
        effective_local_files_only = local_files_only if is_local else False

        self.tokenizer = AutoTokenizer.from_pretrained(
            load_id,
            local_files_only=effective_local_files_only,
            trust_remote_code=trust_remote_code,
            token=hf_token,
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(
            load_id,
            local_files_only=effective_local_files_only,
            trust_remote_code=trust_remote_code,
            token=hf_token,
        ).to(self.device)
        self.model.eval()
        self.max_length = max_length

    def __call__(self, text_input_list: Iterable[str]):
        if isinstance(text_input_list, str):
            text_input_list = [text_input_list]

        encoded_batch = self.tokenizer(
            text_input_list,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded_batch = {k: v.to(self.device) for k, v in encoded_batch.items()}

        with torch.no_grad():
            outputs = self.model(**encoded_batch)
            logits = outputs.logits.detach().cpu().numpy()
        return logits

    def predict(self, texts: Iterable[str]) -> np.ndarray:
        logits = self(texts)
        return np.argmax(logits, axis=-1)

    def get_pred(self, text_input_list: List[str]) -> np.ndarray:  # TextAttack legacy hook
        return self.predict(text_input_list)
