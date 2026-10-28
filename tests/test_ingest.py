"""Tests for GitHub REST API client."""

import base64
from pathlib import Path
from typing import Any

import httpx
import pytest

from linkedin_agent.ingest.github import (
    ETagCache,
    GitHubClient,
    GitHubNotFoundError,
    GitHubRateLimitError,
)


def test_etag_cache_save_and_get(tmp_path: Path) -> None:
    cache_file = tmp_path / "etag.json"
    cache = ETagCache(cache_file)
    assert cache.get("https://api.github.com/test") == (None, None)

    cache.set("https://api.github.com/test", "W/'123'", {"key": "value"})
    etag, body = cache.get("https://api.github.com/test")
    assert etag == "W/'123'"
    assert body == {"key": "value"}

    # Reload from disk
    cache2 = ETagCache(cache_file)
    etag2, body2 = cache2.get("https://api.github.com/test")
    assert etag2 == "W/'123'"
    assert body2 == {"key": "value"}


def test_github_client_get_repo(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def mock_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        assert request.url.path == "/repos/octocat/Hello-World"
        return httpx.Response(
            200,
            json={"name": "Hello-World", "description": "My first repo", "stargazers_count": 42},
            headers={"ETag": '"etag1"'},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "send", mock_send)
    client = GitHubClient(token="dummy", cache=ETagCache(tmp_path / "cache.json"))
    repo = client.get_repo("octocat", "Hello-World")
    assert repo["name"] == "Hello-World"
    assert repo["stargazers_count"] == 42


def test_github_client_304_cache_hit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cache = ETagCache(tmp_path / "cache.json")
    cache.set(
        "https://api.github.com/repos/octocat/Hello-World",
        '"etag1"',
        {"name": "Cached-Repo", "stargazers_count": 99},
    )

    def mock_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        assert request.headers.get("If-None-Match") == '"etag1"'
        return httpx.Response(304, headers={"ETag": '"etag1"'}, request=request)

    monkeypatch.setattr(httpx.Client, "send", mock_send)
    client = GitHubClient(token="dummy", cache=cache)
    repo = client.get_repo("octocat", "Hello-World")
    assert repo["name"] == "Cached-Repo"
    assert repo["stargazers_count"] == 99


def test_github_client_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def mock_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"}, request=request)

    monkeypatch.setattr(httpx.Client, "send", mock_send)
    client = GitHubClient(token="dummy", cache=ETagCache(tmp_path / "cache.json"))
    with pytest.raises(GitHubNotFoundError):
        client.get_repo("octocat", "nonexistent")


def test_github_client_rate_limited(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def mock_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(403, json={"message": "rate limit exceeded"}, request=request)

    monkeypatch.setattr(httpx.Client, "send", mock_send)
    client = GitHubClient(token="dummy", cache=ETagCache(tmp_path / "cache.json"))
    with pytest.raises(GitHubRateLimitError):
        client.get_repo("octocat", "busy-repo")


def test_github_client_get_readme_base64(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    encoded = base64.b64encode(b"# Hello World\nSample content.").decode("ascii")

    def mock_send(self: httpx.Client, request: httpx.Request, **kwargs: Any) -> httpx.Response:
        return httpx.Response(
            200,
            json={"encoding": "base64", "content": encoded},
            request=request,
        )

    monkeypatch.setattr(httpx.Client, "send", mock_send)
    client = GitHubClient(token="dummy", cache=ETagCache(tmp_path / "cache.json"))
    readme = client.get_readme("octocat", "Hello-World")
    assert readme == "# Hello World\nSample content."
