"""Tests for repository ranking and selection engine."""

from pathlib import Path
from typing import Any

from linkedin_agent.context.selector import (
    SelectorConfig,
    calculate_activity_score,
    rank_repositories,
)
from linkedin_agent.ingest.github import GitHubClient
from linkedin_agent.store.db import Database


class MockGitHubRepoClient(GitHubClient):
    """Mock client returning pre-defined repository list."""

    def __init__(self, repos: list[dict[str, Any]]) -> None:
        self.repos = repos

    def list_repos(self, user: str | None = None) -> list[dict[str, Any]]:
        return self.repos


def test_activity_score_calculation() -> None:
    score_fresh, days = calculate_activity_score("2026-10-28T00:00:00Z")
    assert score_fresh >= 0.75

    score_stale, days_stale = calculate_activity_score("2020-01-01T00:00:00Z")
    assert score_stale == 0.1
    assert days_stale > 1000


def test_rank_repositories_unposted_preference(tmp_path: Path) -> None:
    db = Database(tmp_path / "selector_test.db")
    # Mark repo1 as already posted
    db.save_draft("user/repo1", 1, "test text", "sha1", status="PUBLISHED")
    db.record_approval(1, "sha1")
    db.record_post(1, "urn:1", "https://url", "key1")

    repos = [
        {
            "name": "repo1",
            "full_name": "user/repo1",
            "pushed_at": "2026-10-28T00:00:00Z",
            "description": "Repo 1 description",
            "topics": ["python"],
        },
        {
            "name": "repo2",
            "full_name": "user/repo2",
            "pushed_at": "2026-10-27T00:00:00Z",
            "description": "Repo 2 description",
            "topics": ["python"],
        },
    ]

    gh = MockGitHubRepoClient(repos)
    ranked = rank_repositories(gh, db)

    assert len(ranked) == 2
    # Unposted repo2 should outrank already posted repo1
    assert ranked[0].repo == "user/repo2"
    assert ranked[0].is_posted is False
    assert ranked[1].repo == "user/repo1"
    assert ranked[1].is_posted is True


def test_rank_repositories_allowlist_and_denylist(tmp_path: Path) -> None:
    db = Database(tmp_path / "selector_test2.db")
    repos = [
        {"name": "allowed-repo", "full_name": "user/allowed-repo"},
        {"name": "denied-repo", "full_name": "user/denied-repo"},
        {"name": "private-unallowed", "full_name": "user/private-unallowed", "private": True},
    ]

    cfg = SelectorConfig(
        allowlist=["user/allowed-repo", "user/denied-repo"],
        denylist=["user/denied-repo"],
        allow_private=[],
    )

    gh = MockGitHubRepoClient(repos)
    ranked = rank_repositories(gh, db, config=cfg)

    assert len(ranked) == 1
    assert ranked[0].repo == "user/allowed-repo"
