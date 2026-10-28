"""Basic smoke tests for CLI entrypoint."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from linkedin_agent.cli import app
from linkedin_agent.context.models import CommitInfo, ProjectContext

runner = CliRunner()


def test_cli_help() -> None:
    """Test that main CLI displays help and subcommands."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "context" in result.stdout
    assert "draft" in result.stdout
    assert "run" in result.stdout
    assert "auth" in result.stdout
    assert "suggest" in result.stdout


def test_cli_draft_command() -> None:
    """Test agent draft command with mock context and drafter."""
    mock_ctx = ProjectContext(
        repo="octocat/Hello-World",
        description="A great repo",
        languages=["Python"],
    )
    from linkedin_agent.drafter.models import ClaimItem, DraftsResponse, DraftVariant

    mock_drafts = DraftsResponse(
        variants=[
            DraftVariant(
                angle="problem-solution",
                text="Most tools fail at offline mode. Here is how I solved it.",
                hashtags=["#python", "#buildinpublic"],
                claims=[ClaimItem(claim="Uses Python", source="README")],
                warnings=[],
            )
        ]
    )
    with (
        patch("linkedin_agent.cli.build_project_context", return_value=mock_ctx),
        patch("linkedin_agent.cli.generate_drafts", return_value=mock_drafts),
    ):
        result = runner.invoke(app, ["draft", "--repo", "octocat/Hello-World"])
        assert result.exit_code == 0
        assert "Generated 1 draft variants for octocat/Hello-World" in result.stdout
        assert "problem-solution" in result.stdout
        assert "Most tools fail at offline mode" in result.stdout
        assert "Uses Python" in result.stdout


def test_cli_run_dry_run(tmp_path: Path) -> None:
    """Test full pipeline run with --dry-run flag."""
    from linkedin_agent.drafter.models import DraftsResponse, DraftVariant
    from linkedin_agent.store.db import Database

    db = Database(tmp_path / "cli_test.db")
    mock_ctx = ProjectContext(repo="octocat/Hello-World")
    mock_drafts = DraftsResponse(
        variants=[
            DraftVariant(
                angle="problem-solution",
                text="A tested and validated post about software engineering.",
            )
        ]
    )

    with (
        patch("linkedin_agent.cli.Database", return_value=db),
        patch("linkedin_agent.cli.build_project_context", return_value=mock_ctx),
        patch("linkedin_agent.cli.generate_drafts", return_value=mock_drafts),
        patch("typer.prompt", return_value="A"),  # Auto-approve
    ):
        result = runner.invoke(app, ["run", "--repo", "octocat/Hello-World", "--dry-run"])
        assert result.exit_code == 0
        assert "[DRY RUN]" in result.stdout
        assert "verified" in result.stdout


def test_cli_auth_status(tmp_path: Path) -> None:
    """Test auth status CLI command."""
    from linkedin_agent.store.db import Database

    db = Database(tmp_path / "auth_status.db")
    db.save_token("linkedin", "tok_valid", "2026-12-31T00:00:00Z")

    with patch("linkedin_agent.cli.Database", return_value=db):
        result = runner.invoke(app, ["auth", "status"])
        assert result.exit_code == 0
        assert "Authentication & Credentials Status" in result.stdout
        assert "LinkedIn: Active" in result.stdout


def test_cli_suggest_command() -> None:
    """Test suggest CLI command."""
    from linkedin_agent.context.selector import RepoScore

    mock_ranked = [
        RepoScore(
            repo="octocat/Hello-World",
            total_score=0.95,
            activity_score=1.0,
            unposted_score=1.0,
            readme_score=1.0,
            is_posted=False,
            last_pushed_days_ago=2,
            reason="Not yet posted, pushed 2d ago",
        )
    ]
    with patch("linkedin_agent.cli.rank_repositories", return_value=mock_ranked):
        result = runner.invoke(app, ["suggest"])
        assert result.exit_code == 0
        assert "Suggested Repositories" in result.stdout
        assert "octocat/Hello-World" in result.stdout
        assert "0.95" in result.stdout


def test_cli_context_command() -> None:
    """Test agent context command with mock data."""
    mock_ctx = ProjectContext(
        repo="octocat/Hello-World",
        description="A great repo",
        languages=["Python"],
        topics=["learning"],
        stars=10,
        last_push="2026-10-25",
        recent_commits=[CommitInfo(sha="1234567", msg="init commit", date="2026-10-25")],
        readme_excerpt="This is a test readme",
    )
    with patch("linkedin_agent.cli.build_project_context", return_value=mock_ctx):
        result = runner.invoke(app, ["context", "--repo", "octocat/Hello-World"])
        assert result.exit_code == 0
        assert "Project Context: octocat/Hello-World" in result.stdout
        assert "A great repo" in result.stdout
        assert "init commit" in result.stdout

