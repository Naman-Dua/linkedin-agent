"""LLM client interface and factory."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod


class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMClient(ABC):
    """Abstract interface for LLM completion providers."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Generate text completion from system and user prompts."""


def get_llm_client(
    provider: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> LLMClient:
    """Instantiate appropriate LLM client based on environment or parameters."""
    selected_provider = (provider or os.getenv("LLM_PROVIDER") or "gemini").lower()

    if selected_provider == "gemini":
        from linkedin_agent.llm.gemini import GeminiClient

        return GeminiClient(api_key=api_key, model=model)
    elif selected_provider == "claude":
        from linkedin_agent.llm.claude import ClaudeClient

        return ClaudeClient(api_key=api_key, model=model)
    else:
        raise ValueError(
            f"Unsupported LLM provider: {selected_provider}. Use 'gemini' or 'claude'."
        )
