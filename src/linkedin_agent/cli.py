"""Command-line interface for LinkedIn Post Agent."""

import typer

from linkedin_agent.context.builder import build_project_context
from linkedin_agent.ingest.github import GitHubError

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
    try:
        ctx = build_project_context(repo)
    except GitHubError as e:
        typer.secho(f"Error fetching repository context: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    typer.secho(f"\n=== Project Context: {ctx.repo} ===", fg=typer.colors.CYAN, bold=True)
    if ctx.description:
        typer.echo(f"Description: {ctx.description}")
    if ctx.languages:
        typer.echo(f"Languages: {', '.join(ctx.languages)}")
    if ctx.topics:
        typer.echo(f"Topics: {', '.join(ctx.topics)}")
    typer.echo(f"Stars: {ctx.stars} | Last Push: {ctx.last_push}")
    if ctx.homepage:
        typer.echo(f"Homepage: {ctx.homepage}")

    if ctx.recent_commits:
        typer.secho("\nRecent Commits:", fg=typer.colors.YELLOW)
        for c in ctx.recent_commits:
            typer.echo(f"  [{c.sha}] {c.msg} ({c.date[:10]})")

    if ctx.releases:
        typer.secho("\nReleases:", fg=typer.colors.YELLOW)
        for r in ctx.releases:
            typer.echo(f"  [{r.tag}] {r.name} ({r.date[:10]})")

    if ctx.local_notes:
        typer.secho("\nLocal Notes:", fg=typer.colors.GREEN)
        typer.echo(ctx.local_notes[:500] + ("..." if len(ctx.local_notes) > 500 else ""))

    if ctx.readme_excerpt:
        typer.secho("\nREADME Excerpt:", fg=typer.colors.MAGENTA)
        typer.echo(ctx.readme_excerpt[:500] + ("..." if len(ctx.readme_excerpt) > 500 else ""))
    typer.echo("")


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
