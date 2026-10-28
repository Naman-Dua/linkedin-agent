"""Basic smoke tests for CLI entrypoint."""

from typer.testing import CliRunner

from linkedin_agent.cli import app

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
