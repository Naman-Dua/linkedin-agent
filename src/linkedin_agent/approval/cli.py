"""Interactive CLI approval interface."""

from __future__ import annotations

import click
import typer

from linkedin_agent.approval.gate import ApprovalGate
from linkedin_agent.audit.log import audit_log
from linkedin_agent.drafter.models import DraftVariant
from linkedin_agent.store.models import DraftRecord


def present_draft_for_approval(
    gate: ApprovalGate,
    repo: str,
    variant_no: int,
    variant: DraftVariant,
) -> DraftRecord | None:
    """Interactively present a draft to the user and handle approve/edit/skip actions."""
    current_text = variant.text
    current_draft = gate.register_draft(repo=repo, variant_no=variant_no, text=current_text)

    while True:
        typer.secho(
            f"\n=== Draft Variant {current_draft.variant_no} [{variant.angle}] ===",
            fg=typer.colors.CYAN,
            bold=True,
        )
        typer.echo(current_draft.text)
        if variant.hashtags:
            typer.secho(f"\nHashtags: {' '.join(variant.hashtags)}", fg=typer.colors.BLUE)
        if variant.warnings:
            typer.secho("\nWarnings:", fg=typer.colors.YELLOW)
            for w in variant.warnings:
                typer.echo(f"  ⚠ {w}")

        typer.secho(f"\nContent SHA256: {current_draft.text_sha256[:12]}...", fg=typer.colors.WHITE)
        choice = typer.prompt(
            "\nAction: [A]pprove / [E]dit / [S]kip / [R]egenerate",
            default="A",
        ).strip().upper()

        if choice == "A":
            approval = gate.approve_draft(current_draft.id, channel="cli")
            audit_log(
                "draft_approved",
                {
                    "draft_id": current_draft.id,
                    "repo": repo,
                    "sha256": approval.text_sha256,
                    "channel": "cli",
                },
            )
            typer.secho("✓ Draft approved successfully!", fg=typer.colors.GREEN, bold=True)
            return current_draft

        elif choice == "E":
            edited_text = click.edit(current_draft.text)
            if not edited_text or edited_text.strip() == current_draft.text.strip():
                typer.echo("No changes detected in editor.")
                continue

            current_draft = gate.edit_draft(current_draft.id, edited_text.strip())
            audit_log(
                "draft_edited",
                {
                    "original_draft_id": current_draft.parent_draft_id,
                    "new_draft_id": current_draft.id,
                    "new_sha256": current_draft.text_sha256,
                },
            )
            typer.secho(
                "Draft updated. Prior approval invalidated. Please review new draft.",
                fg=typer.colors.YELLOW,
            )

        elif choice == "S":
            gate.db.update_draft_status(current_draft.id, "SKIPPED")
            audit_log("draft_skipped", {"draft_id": current_draft.id, "repo": repo})
            typer.secho("Draft skipped.", fg=typer.colors.YELLOW)
            return None

        elif choice == "R":
            gate.db.update_draft_status(current_draft.id, "REGENERATED")
            audit_log("draft_regenerate_requested", {"draft_id": current_draft.id, "repo": repo})
            typer.secho("Regeneration requested.", fg=typer.colors.YELLOW)
            return None

        else:
            typer.echo("Invalid choice. Please enter A, E, S, or R.")
