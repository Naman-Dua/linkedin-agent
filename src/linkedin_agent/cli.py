"""Command-line interface for LinkedIn Post Agent."""

import os
from datetime import UTC, datetime

import typer

from linkedin_agent.approval.cli import present_draft_for_approval
from linkedin_agent.approval.gate import ApprovalGate
from linkedin_agent.context.builder import build_project_context
from linkedin_agent.drafter.drafter import generate_drafts
from linkedin_agent.ingest.github import GitHubClient, GitHubError
from linkedin_agent.llm.base import LLMError
from linkedin_agent.publisher.linkedin import LinkedInPublisher, LinkedInPublishError
from linkedin_agent.publisher.oauth import run_oauth_flow
from linkedin_agent.store.db import Database

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
    instruction: str = typer.Option(
        None, "--instruction", "-i", help="Optional drafting angle or prompt"
    ),
) -> None:
    """Generate grounded LinkedIn post variants for a repository."""
    try:
        ctx = build_project_context(repo)
    except GitHubError as e:
        typer.secho(f"Error fetching context: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    try:
        drafts = generate_drafts(ctx, instruction=instruction)
    except LLMError as e:
        typer.secho(f"Error calling LLM: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    if not drafts.variants:
        typer.secho("\nNo drafts could be generated.", fg=typer.colors.YELLOW)
        if drafts.missing_context:
            typer.echo("Missing context:")
            for m in drafts.missing_context:
                typer.echo(f"  - {m}")
        return

    typer.secho(
        f"\nGenerated {len(drafts.variants)} draft variants for {ctx.repo}:\n",
        fg=typer.colors.GREEN,
        bold=True,
    )
    for idx, v in enumerate(drafts.variants, start=1):
        typer.secho(f"--- [Variant {idx}: {v.angle}] ---", fg=typer.colors.CYAN, bold=True)
        typer.echo(v.text)
        if v.hashtags:
            typer.secho(f"\nHashtags: {' '.join(v.hashtags)}", fg=typer.colors.BLUE)
        if v.claims:
            typer.secho("\nCited Claims:", fg=typer.colors.YELLOW)
            for c in v.claims:
                typer.echo(f"  • {c.claim} (Source: {c.source})")
        if v.warnings:
            typer.secho("\nWarnings:", fg=typer.colors.RED)
            for w in v.warnings:
                typer.echo(f"  ⚠ {w}")
        typer.echo("\n" + "=" * 50 + "\n")


@app.command()
def run(
    repo: str = typer.Option(..., "--repo", "-r", help="Repository name to process"),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--no-dry-run",
        help="Run without publishing to LinkedIn (default: True)",
    ),
    variant_no: int = typer.Option(1, "--variant", "-v", help="Variant index to review (1-3)"),
) -> None:
    """Run full pipeline: ingest, draft, human approval, and optional publish."""
    db = Database()
    gate = ApprovalGate(db)

    # 1. Ingest context
    try:
        ctx = build_project_context(repo)
    except GitHubError as e:
        typer.secho(f"Error fetching context: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    # 2. Draft post variants
    try:
        drafts = generate_drafts(ctx)
    except LLMError as e:
        typer.secho(f"Error calling LLM: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    if not drafts.variants:
        typer.secho("No draft variants could be generated.", fg=typer.colors.YELLOW)
        return

    idx = max(0, min(variant_no - 1, len(drafts.variants) - 1))
    chosen_variant = drafts.variants[idx]

    # 3. Present for human approval
    approved_draft = present_draft_for_approval(gate, repo, idx + 1, chosen_variant)
    if not approved_draft:
        typer.echo("Pipeline stopped without approved draft.")
        return

    # 4. Mandatory Cryptographic Gate Check
    approval = gate.verify_can_publish(approved_draft.text)

    # 5. Publish via LinkedInPublisher
    publisher = LinkedInPublisher(db)
    try:
        result = publisher.publish_post(
            draft_id=approved_draft.id,
            repo=repo,
            text=approved_draft.text,
            dry_run=dry_run,
        )
    except LinkedInPublishError as e:
        typer.secho(f"Publish failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e

    if result.is_dry_run:
        typer.secho(
            f"\n[DRY RUN] Content hash {approval.text_sha256[:8]} verified.",
            fg=typer.colors.GREEN,
            bold=True,
        )
        typer.secho(
            f"Mock URN: {result.urn}\nAudit log updated. Publication skipped (--dry-run).",
            fg=typer.colors.CYAN,
        )
    else:
        typer.secho(f"\n✓ Post published live: {result.urn}", fg=typer.colors.GREEN, bold=True)
        if result.url:
            typer.echo(f"URL: {result.url}")


auth_app = typer.Typer(help="Manage authentication and token status", no_args_is_help=True)
app.add_typer(auth_app, name="auth")


@auth_app.command(name="login")
def auth_login(
    port: int = typer.Option(8080, "--port", "-p", help="Local callback port"),
) -> None:
    """Run interactive LinkedIn OAuth login flow."""
    db = Database()
    try:
        run_oauth_flow(db, port=port)
        typer.secho("✓ Successfully authenticated with LinkedIn!", fg=typer.colors.GREEN, bold=True)
    except Exception as e:
        typer.secho(f"Authentication failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from e


@auth_app.command(name="status")
def auth_status() -> None:
    """Check status and expiration of GitHub and LinkedIn credentials."""
    db = Database()
    typer.secho("\n=== Authentication & Credentials Status ===", fg=typer.colors.CYAN, bold=True)

    # 1. GitHub Check
    gh_token = os.getenv("GITHUB_TOKEN")
    if gh_token:
        try:
            gh_client = GitHubClient(token=gh_token)
            user_data = gh_client._get("/user")
            login = user_data.get("login", "unknown")
            typer.secho(f"GitHub: Authenticated as '{login}' (Token set)", fg=typer.colors.GREEN)
        except Exception as e:
            typer.secho(f"GitHub: Token error ({e})", fg=typer.colors.RED)
    else:
        typer.secho(
            "GitHub: No token configured (unauthenticated API only)",
            fg=typer.colors.YELLOW,
        )

    # 2. LinkedIn Check
    tok_info = db.get_token("linkedin")
    if tok_info:
        token, expires_at_str = tok_info
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            days_left = (expires_at - datetime.now(UTC)).days
            if days_left <= 0:
                typer.secho(
                    "LinkedIn: Token EXPIRED! Run 'agent auth login'.",
                    fg=typer.colors.RED,
                    bold=True,
                )
            elif days_left <= 7:
                typer.secho(
                    f"LinkedIn: Active (EXPIRES IN {days_left} DAYS! Re-auth recommended)",
                    fg=typer.colors.YELLOW,
                    bold=True,
                )
            else:
                typer.secho(
                    f"LinkedIn: Active ({days_left} days remaining until expiry)",
                    fg=typer.colors.GREEN,
                )
        except Exception:
            typer.secho("LinkedIn: Token present in database.", fg=typer.colors.GREEN)
    elif os.getenv("LINKEDIN_ACCESS_TOKEN"):
        typer.secho("LinkedIn: Access token loaded from environment.", fg=typer.colors.GREEN)
    else:
        typer.secho("LinkedIn: Not authenticated. Run 'agent auth login'.", fg=typer.colors.YELLOW)

    dry_run_env = os.getenv("DRY_RUN", "true").lower() in ("1", "true", "yes")
    typer.echo(f"\nDefault DRY_RUN: {dry_run_env}\n")


@app.command()
def suggest() -> None:
    """Suggest which repository to post about next based on activity and history."""
    typer.echo("Analyzing repositories for suggestions...")


if __name__ == "__main__":
    app()
