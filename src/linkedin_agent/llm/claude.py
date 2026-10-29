"""Anthropic Claude LLM provider implementation."""

from __future__ import annotations

import json
import os
import time
from typing import Any

import httpx

from linkedin_agent.llm.base import LLMClient, LLMError

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class ClaudeClient(LLMClient):
    """Client for Anthropic Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
        self.model = model or os.getenv("LLM_MODEL") or "claude-3-5-sonnet-20241022"
        self.timeout = timeout

    def complete(self, system: str, user: str) -> str:
        """Call Anthropic messages endpoint."""
        if not self.api_key:
            raise LLMError(
                "Anthropic API key not configured. Set LLM_API_KEY or ANTHROPIC_API_KEY."
            )

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": 2048,
            "temperature": 0.7,
        }

        retries = 2
        for attempt in range(retries + 1):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    resp = client.post(ANTHROPIC_API_URL, headers=headers, json=payload)
                    if resp.status_code == 429 or resp.status_code >= 500:
                        if attempt < retries:
                            time.sleep(2.0 * (attempt + 1))
                            continue
                    if resp.is_error:
                        raise LLMError(f"Claude API error ({resp.status_code}): {resp.text}")

                    data = resp.json()
                    content: list[dict[str, Any]] = data.get("content", [])
                    if not content or "text" not in content[0]:
                        raise LLMError(f"Malformed response from Claude: {data}")
                    return str(content[0]["text"])
            except httpx.RequestError as exc:
                if attempt < retries:
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise LLMError(f"Network error communicating with Claude API: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise LLMError(f"Failed to parse Claude response JSON: {exc}") from exc

        raise LLMError("Failed to get completion from Claude after retries.")
