"""Basic smoke tests for CLI entrypoint."""

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


def test_cli_auth_status_help() -> None:
    """Test that auth status subcommand help works."""
    result = runner.invoke(app, ["auth", "--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout


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

