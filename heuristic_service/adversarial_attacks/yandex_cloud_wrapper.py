"""TextAttack model wrapper for Yandex Cloud foundation models used as classifiers."""

from __future__ import annotations

import json
import os
import re
import time
from typing import Iterable, List, Optional, Sequence

import numpy as np
import requests
from textattack.models.wrappers import ModelWrapper

from rag_service.shared.get_private_key import get_private_key


DEFAULT_SYSTEM_PROMPT = (
    "Ты выступаешь в роли бинарного классификатора (метки '0' и '1'). "
    "Для каждого пользовательского текста ты должен вернуть JSON без дополнительного текста. "
    "Структура ответа: {\"probabilities\": {\"0\": p0, \"1\": p1}, \"label\": \"0 или 1\"}. "
    "p0 и p1 — вероятности и должны суммироваться до 1."
)

DEFAULT_USER_PROMPT_TEMPLATE = (
    "Проанализируй следующий текст пользователя и оцени вероятность классов 0 и 1. "
    "Возвращай только JSON: {\"probabilities\": {\"0\": ..., \"1\": ...}, \"label\": ...}.\n\n"
    "Текст: {text}"
)


class YandexCloudClassifierWrapper(ModelWrapper):
    """Adapter that queries Yandex Cloud completion endpoint and extracts logits."""

    def __init__(
        self,
        *,
        labels: Sequence[str] = ("0", "1"),
        folder_id: Optional[str] = None,
        key_id: Optional[str] = None,
        service_account_id: Optional[str] = None,
        private_key: Optional[str] = None,
        model: str = "yandexgpt-lite",
        system_prompt: Optional[str] = None,
        user_prompt_template: str = DEFAULT_USER_PROMPT_TEMPLATE,
        temperature: float = 0.2,
        max_tokens: int = 200,
        request_timeout: int = 30,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.labels = [str(label) for label in labels]
        self.folder_id = folder_id or os.getenv("FOLDER_ID")
        self.key_id = key_id or os.getenv("KEY_ID")
        self.service_account_id = service_account_id or os.getenv("SERVICE_ACCOUNT_ID")
        self.private_key = private_key or get_private_key()
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.user_prompt_template = user_prompt_template
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.session = session or requests.Session()

        missing = [name for name, value in (
            ("FOLDER_ID", self.folder_id),
            ("KEY_ID", self.key_id),
            ("SERVICE_ACCOUNT_ID", self.service_account_id),
            ("PRIVATE_KEY", self.private_key),
        ) if not value]
        if missing:
            raise ValueError(f"Missing Yandex Cloud credentials: {', '.join(missing)}")

        self._iam_token: Optional[str] = None
        self._token_expires: float = 0.0

    # --- IAM token helpers -------------------------------------------------
    def _ensure_iam_token(self) -> str:
        now = time.time()
        if self._iam_token and now < self._token_expires:
            return self._iam_token

        payload = {
            "aud": "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            "iss": self.service_account_id,
            "iat": int(now),
            "exp": int(now) + 360,
        }

        encoded = self._encode_jwt(payload)

        response = self.session.post(
            "https://iam.api.cloud.yandex.net/iam/v1/tokens",
            json={"jwt": encoded},
            timeout=self.request_timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to obtain IAM token ({response.status_code}): {response.text}"
            )

        data = response.json()
        token = data.get("iamToken")
        if not token:
            raise RuntimeError("IAM token response missing 'iamToken'")

        self._iam_token = token
        self._token_expires = now + 3500  # slightly less than 1h
        return token

    def _encode_jwt(self, payload: dict) -> str:
        import jwt  # local import to avoid global dependency if unused

        return jwt.encode(
            payload,
            self.private_key,
            algorithm="PS256",
            headers={"kid": self.key_id},
        )

    # --- Request helpers ---------------------------------------------------
    def _build_messages(self, text: str) -> list[dict]:
        return [
            {"role": "system", "text": self.system_prompt},
            {
                "role": "user",
                "text": self.user_prompt_template.format(text=text),
            },
        ]

    def _call_completion(self, text: str) -> str:
        token = self._ensure_iam_token()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-folder-id": self.folder_id,
        }
        payload = {
            "modelUri": f"gpt://{self.folder_id}/{self.model}",
            "completionOptions": {
                "stream": False,
                "temperature": self.temperature,
                "maxTokens": self.max_tokens,
            },
            "messages": self._build_messages(text),
        }

        response = self.session.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers=headers,
            json=payload,
            timeout=self.request_timeout,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Yandex completion error ({response.status_code}): {response.text}"
            )

        try:
            result = response.json()["result"]["alternatives"][0]["message"]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"Unexpected completion payload: {response.text}"
            ) from exc

        return result

    # --- Parsing -----------------------------------------------------------
    _json_pattern = re.compile(r"\{.*\}", re.DOTALL)

    def _parse_probabilities(self, text: str) -> dict[str, float]:
        candidate = text
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            match = self._json_pattern.search(text)
            if not match:
                raise ValueError(f"Cannot parse JSON from response: {text}")
            data = json.loads(match.group(0))

        probs = None
        for key in ("probabilities", "label_probabilities", "scores"):
            if isinstance(data, dict) and key in data:
                probs = data[key]
                break
        if probs is None or not isinstance(probs, dict):
            raise ValueError(f"No probabilities field in response: {data}")

        converted = {}
        for label in self.labels:
            value = probs.get(label)
            if value is None and label.startswith("LABEL_"):
                # Try fallback to numeric suffix
                alt_key = label.split("LABEL_")[-1]
                value = probs.get(alt_key)
            if value is None:
                raise ValueError(f"Missing probability for label '{label}' in {probs}")
            converted[label] = float(value)

        total = sum(converted.values())
        if total <= 0:
            raise ValueError(f"Probabilities sum to non-positive value: {converted}")

        # Normalize to avoid drift in case the model does not sum to 1 exactly
        converted = {k: v / total for k, v in converted.items()}
        return converted

    # --- TextAttack interface ---------------------------------------------
    def __call__(self, text_input_list: Iterable[str]):
        if isinstance(text_input_list, str):
            text_input_list = [text_input_list]

        logits_rows: List[np.ndarray] = []
        for text in text_input_list:
            raw_answer = self._call_completion(text)
            probs = self._parse_probabilities(raw_answer)
            probabilities = np.array([probs[label] for label in self.labels], dtype=np.float32)
            logits = np.log(np.clip(probabilities, 1e-12, 1.0))
            logits_rows.append(logits)

        return np.vstack(logits_rows)

    def predict(self, texts: Iterable[str]) -> np.ndarray:
        logits = self(texts)
        return np.argmax(logits, axis=-1)

