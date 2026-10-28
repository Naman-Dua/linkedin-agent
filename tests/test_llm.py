"""Tests for LLM clients."""

from typing import Any

import httpx
import pytest

from linkedin_agent.llm.base import LLMError, get_llm_client
from linkedin_agent.llm.claude import ClaudeClient
from linkedin_agent.llm.gemini import GeminiClient


def test_gemini_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": '{"variants": []}'}]}}
                ]
            },
            request=req,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = GeminiClient(api_key="fake-key")
    res = client.complete("system prompt", "user prompt")
    assert res == '{"variants": []}'


def test_gemini_client_missing_key() -> None:
    client = GeminiClient(api_key="")
    with pytest.raises(LLMError):
        client.complete("system", "user")


def test_claude_client_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"content": [{"text": '{"variants": []}'}]},
            request=req,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    client = ClaudeClient(api_key="fake-key")
    res = client.complete("system prompt", "user prompt")
    assert res == '{"variants": []}'


def test_get_llm_client_factory() -> None:
    gemini = get_llm_client(provider="gemini", api_key="dummy")
    assert isinstance(gemini, GeminiClient)

    claude = get_llm_client(provider="claude", api_key="dummy")
    assert isinstance(claude, ClaudeClient)

    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        get_llm_client(provider="unsupported")
