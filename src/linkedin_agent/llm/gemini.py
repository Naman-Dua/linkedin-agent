"""Google Gemini LLM provider implementation."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import httpx

from linkedin_agent.llm.base import LLMClient, LLMError

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash"]


class GeminiClient(LLMClient):
    """Client for Google Gemini REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("LLM_API_KEY") or os.getenv("GEMINI_API_KEY") or ""
        raw_model = (model or os.getenv("LLM_MODEL") or "gemini-3.5-flash").strip()
        if raw_model.startswith("models/"):
            raw_model = raw_model[7:]
        self.model = raw_model.lower()
        self.timeout = timeout

    def _execute_completion(self, model: str, system: str, user: str) -> str:
        """Call Gemini generateContent endpoint for a specific model."""
        url = f"{GEMINI_API_URL.format(model=model)}?key={self.api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.7,
                "response_mime_type": "application/json",
            },
        }

        retries = 2
        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if resp.status_code == 429 or resp.status_code >= 500:
                        if attempt < retries:
                            time.sleep(2.0 * (attempt + 1))
                            continue
                    if resp.is_error:
                        raise LLMError(f"Gemini API error ({resp.status_code}): {resp.text}")

                    data = resp.json()
                    candidates: list[dict[str, Any]] = data.get("candidates", [])
                    if not candidates:
                        raise LLMError(f"No candidates returned by Gemini: {data}")
                    content = candidates[0].get("content", {})
                    parts: list[dict[str, Any]] = content.get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise LLMError(f"Malformed response parts from Gemini: {data}")
                    return str(parts[0]["text"])
            except httpx.RequestError as exc:
                if attempt < retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise LLMError(f"Network error communicating with Gemini API: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise LLMError(f"Failed to parse Gemini response JSON: {exc}") from exc

        raise LLMError("Failed to get completion from Gemini after retries.")

    def complete(self, system: str, user: str) -> str:
        """Generate completion with automated fallback on high demand (503/404/429)."""
        if not self.api_key:
            raise LLMError("Gemini API key not configured. Set LLM_API_KEY or pass api_key.")

        models_to_try = [self.model]
        for fb in FALLBACK_MODELS:
            if fb not in models_to_try:
                models_to_try.append(fb)

        last_error: Exception | None = None
        for m in models_to_try:
            try:
                return self._execute_completion(m, system, user)
            except LLMError as exc:
                last_error = exc
                err_msg = str(exc)
                if any(code in err_msg for code in ("503", "404", "429")):
                    logger.warning(
                        "Gemini model %s unavailable (%s). Trying fallback...", m, err_msg[:60]
                    )
                    continue
                raise

        if last_error:
            raise last_error
        raise LLMError("Gemini completion failed across all available models.")
