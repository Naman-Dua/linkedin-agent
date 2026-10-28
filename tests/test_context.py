"""Tests for ProjectContext builder."""

from pathlib import Path
from typing import Any

import pytest

from linkedin_agent.context.builder import build_project_context
from linkedin_agent.ingest.github import GitHubClient


class DummyGitHubClient(GitHubClient):
    """Mock GitHub client returning pre-canned data."""

    def __init__(self) -> None:
        pass

    def parse_repo_path(self, repo_spec: str) -> tuple[str, str]:
        return "owner", "cool-project"

    def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        return {
            "name": "cool-project",
            "description": "Project with token ghp_123456789012345678901234567890123456 here",
            "stargazers_count": 15,
            "pushed_at": "2026-10-25T12:00:00Z",
            "topics": ["python", "cli"],
            "homepage": "https://example.com",
        }

    def get_readme(self, owner: str, repo: str) -> str | None:
        return "# Cool Project\nContact me at author@company.com. " + ("A" * 3000)

    def get_languages(self, owner: str, repo: str) -> list[str]:
        return ["Python", "Shell"]

    def get_commits(self, owner: str, repo: str, limit: int = 5) -> list[dict[str, Any]]:
        return [
            {
                "sha": "1234567890abcdef",
                "commit": {
                    "message": "fix: update api_key='secret12345' configuration",
                    "author": {"date": "2026-10-24T10:00:00Z"},
                },
            }
        ]

    def get_releases(self, owner: str, repo: str, limit: int = 3) -> list[dict[str, Any]]:
        return [
            {
                "tag_name": "v1.0.0",
                "name": "First Release",
                "published_at": "2026-10-20T00:00:00Z",
                "body": "Initial release with password = 'hunter2'",
            }
        ]


def test_build_project_context_redaction_and_trimming(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Point local notes to mock return
    monkeypatch.setattr(
        "linkedin_agent.context.builder.load_local_notes",
        lambda repo: "Note: key=sk_live_12345678",
    )

    dummy_client = DummyGitHubClient()
    ctx = build_project_context("owner/cool-project", github_client=dummy_client)

    assert ctx.repo == "owner/cool-project"
    assert ctx.stars == 15
    assert ctx.languages == ["Python", "Shell"]
    assert ctx.topics == ["python", "cli"]

    # Redaction checks
    assert ctx.description is not None
    assert "[REDACTED_GITHUB_TOKEN]" in ctx.description
    assert "ghp_" not in ctx.description

    assert ctx.readme_excerpt is not None
    assert "[REDACTED_EMAIL]" in ctx.readme_excerpt
    assert "author@company.com" not in ctx.readme_excerpt
    assert len(ctx.readme_excerpt) <= 2100

    assert len(ctx.recent_commits) == 1
    assert ctx.recent_commits[0].sha == "1234567"
    assert "api_key=[REDACTED_SECRET]" in ctx.recent_commits[0].msg

    assert len(ctx.releases) == 1
    assert ctx.releases[0].tag == "v1.0.0"
    assert ctx.releases[0].body is not None
    assert "password=[REDACTED_SECRET]" in ctx.releases[0].body

    assert ctx.local_notes is not None
    assert "key=[REDACTED_SECRET]" in ctx.local_notes

