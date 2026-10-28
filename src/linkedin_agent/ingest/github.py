"""GitHub REST API client with ETag caching and rate-limit awareness."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubError(Exception):
    """Base exception for GitHub API errors."""


class GitHubNotFoundError(GitHubError):
    """Raised when repository or resource is not found (404)."""


class GitHubRateLimitError(GitHubError):
    """Raised when GitHub API rate limit is exceeded (403/429)."""


class ETagCache:
    """Simple JSON-backed cache for HTTP ETags and responses."""

    def __init__(self, cache_file: Path | None = None) -> None:
        if cache_file is None:
            cache_dir = Path.home() / ".cache" / "linkedin_agent"
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = cache_dir / "etag_cache.json"
        self.cache_file = cache_file
        self._data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        if self.cache_file.exists():
            try:
                return json.loads(self.cache_file.read_text(encoding="utf-8"))  # type: ignore[no-any-return]
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._data), encoding="utf-8")
        except Exception:
            pass

    def get(self, url: str) -> tuple[str | None, Any | None]:
        entry = self._data.get(url)
        if entry:
            return entry.get("etag"), entry.get("body")
        return None, None

    def set(self, url: str, etag: str | None, body: Any) -> None:
        self._data[url] = {"etag": etag, "body": body}
        self.save()


class GitHubClient:
    """Client for fetching repository data from GitHub REST API."""

    def __init__(
        self,
        token: str | None = None,
        cache: ETagCache | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.cache = cache or ETagCache()
        self.timeout = timeout

    def _headers(self, etag: str | None = None) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "LinkedInPostAgent/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if etag:
            headers["If-None-Match"] = etag
        return headers

    def _get(self, path: str) -> Any:
        url = f"{GITHUB_API_BASE}{path}" if path.startswith("/") else path
        cached_etag, cached_body = self.cache.get(url)

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._headers(cached_etag))

            if response.status_code == 304 and cached_body is not None:
                return cached_body

            if response.status_code == 404:
                raise GitHubNotFoundError(f"Resource not found: {url}")
            if response.status_code in (403, 429):
                raise GitHubRateLimitError(f"Rate limited or forbidden: {response.text}")
            if response.is_error:
                raise GitHubError(f"GitHub API error ({response.status_code}): {response.text}")

            data = response.json()
            new_etag = response.headers.get("ETag")
            if new_etag:
                self.cache.set(url, new_etag, data)
            return data

    def parse_repo_path(self, repo_spec: str) -> tuple[str, str]:
        """Convert 'owner/repo' or 'repo' into (owner, repo).

        If only 'repo' is given and GITHUB_TOKEN is set, queries user endpoint to find owner.
        """
        if "/" in repo_spec:
            parts = repo_spec.split("/", 1)
            return parts[0], parts[1]

        # Single repo name: attempt to get authenticated user or fallback to repo_spec as owner
        try:
            user_data = self._get("/user")
            owner = str(user_data.get("login", repo_spec))
            return owner, repo_spec
        except Exception:
            return repo_spec, repo_spec

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata."""
        return self._get(f"/repos/{owner}/{repo}")  # type: ignore[no-any-return]

    def get_readme(self, owner: str, repo: str) -> str | None:
        """Fetch repository README content."""
        try:
            data = self._get(f"/repos/{owner}/{repo}/readme")
            encoding = data.get("encoding")
            content = data.get("content", "")
            if encoding == "base64" and content:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            return str(content) if content else None
        except GitHubNotFoundError:
            return None

    def get_languages(self, owner: str, repo: str) -> list[str]:
        """Fetch top languages used in repository."""
        try:
            data = self._get(f"/repos/{owner}/{repo}/languages")
            if isinstance(data, dict):
                return list(data.keys())
            return []
        except GitHubError:
            return []

    def get_commits(self, owner: str, repo: str, limit: int = 5) -> list[dict[str, Any]]:
        """Fetch recent commits."""
        try:
            data = self._get(f"/repos/{owner}/{repo}/commits?per_page={limit}")
            if isinstance(data, list):
                return [dict(item) for item in data if isinstance(item, dict)]
            return []
        except GitHubError:
            return []

    def get_releases(self, owner: str, repo: str, limit: int = 3) -> list[dict[str, Any]]:
        """Fetch recent releases."""
        try:
            data = self._get(f"/repos/{owner}/{repo}/releases?per_page={limit}")
            if isinstance(data, list):
                return [dict(item) for item in data if isinstance(item, dict)]
            return []
        except GitHubError:
            return []

    def list_repos(self, user: str | None = None) -> list[dict[str, Any]]:
        """List repositories for user or authenticated user."""
        if user:
            path = f"/users/{user}/repos?per_page=100&sort=pushed"
        else:
            path = "/user/repos?per_page=100&sort=pushed"
        data = self._get(path)
        if isinstance(data, list):
            return [dict(item) for item in data if isinstance(item, dict)]
        return []
