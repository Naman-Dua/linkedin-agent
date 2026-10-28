"""Command-line interface for LinkedIn Post Agent."""

import typer

app = typer.Typer(
    name="agent",
    help="LinkedIn Post Agent — reads GitHub repos & notes, drafts posts under human approval.",
    no_args_is_help=True,
)


@app.command()
def context(
    repo: str = typer.Option(..., "--repo", "-r", help="Repository name to inspect"),
) -> None:
    """Fetch and display summarized context for a repository."""
    typer.echo(f"Inspecting context for repository: {repo}")


@app.command()
def draft(
    repo: str = typer.Option(..., "--repo", "-r", help="Repository name to draft for"),
) -> None:
    """Generate grounded LinkedIn post variants for a repository."""
    typer.echo(f"Drafting post variants for repository: {repo}")


@app.command()
def run(
    repo: str = typer.Option(..., "--repo", "-r", help="Repository name to process"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Run without publishing to LinkedIn (default: True)",
    ),
) -> None:
    """Run full pipeline: ingest, draft, human approval, and optional publish."""
    typer.echo(f"Running pipeline for {repo} (dry_run={dry_run})")


auth_app = typer.Typer(help="Manage authentication and token status", no_args_is_help=True)
app.add_typer(auth_app, name="auth")


@auth_app.command(name="status")
def auth_status() -> None:
    """Check status and expiration of GitHub and LinkedIn credentials."""
    typer.echo("Checking authentication status...")


@app.command()
def suggest() -> None:
    """Suggest which repository to post about next based on activity and history."""
    typer.echo("Analyzing repositories for suggestions...")


if __name__ == "__main__":
    app()
