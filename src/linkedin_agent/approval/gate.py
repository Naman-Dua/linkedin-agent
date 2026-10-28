"""Cryptographic approval gate and draft state machine."""

from __future__ import annotations

import hashlib

from linkedin_agent.store.db import Database
from linkedin_agent.store.models import ApprovalRecord, DraftRecord


class ApprovalError(Exception):
    """Base exception for approval gate errors."""


class UnapprovedContentError(ApprovalError):
    """Raised when publication is attempted on content lacking a matching approval hash."""


def compute_sha256(text: str) -> str:
    """Compute canonical SHA-256 hex digest of text."""
    normalized = text.strip().encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


class ApprovalGate:
    """Enforces cryptographic approval invariant for content publication."""

    def __init__(self, db: Database) -> None:
        self.db = db

    def register_draft(
        self,
        repo: str,
        variant_no: int,
        text: str,
        parent_draft_id: int | None = None,
    ) -> DraftRecord:
        """Create new draft in PENDING_APPROVAL state with its text hash."""
        sha = compute_sha256(text)
        draft_id = self.db.save_draft(
            repo=repo,
            variant_no=variant_no,
            text=text,
            text_sha256=sha,
            status="PENDING_APPROVAL",
            parent_draft_id=parent_draft_id,
        )
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ApprovalError(f"Failed to persist draft for {repo}")
        return draft

    def approve_draft(self, draft_id: int, channel: str = "cli") -> ApprovalRecord:
        """Approve a draft by binding its exact SHA-256 hash."""
        draft = self.db.get_draft(draft_id)
        if not draft:
            raise ApprovalError(f"Draft {draft_id} not found.")

        # Compute hash directly from draft text to ensure invariant
        sha = compute_sha256(draft.text)
        self.db.record_approval(draft_id=draft_id, text_sha256=sha, channel=channel)
        approval = self.db.get_approval_by_hash(sha)
        if not approval:
            raise ApprovalError("Approval record creation failed.")
        return approval

    def edit_draft(self, original_draft_id: int, new_text: str) -> DraftRecord:
        """Record an edit. Creates a new draft requiring fresh approval."""
        original = self.db.get_draft(original_draft_id)
        if not original:
            raise ApprovalError(f"Original draft {original_draft_id} not found.")

        self.db.update_draft_status(original_draft_id, "EDITED")
        return self.register_draft(
            repo=original.repo,
            variant_no=original.variant_no,
            text=new_text,
            parent_draft_id=original.id,
        )

    def verify_can_publish(self, text: str) -> ApprovalRecord:
        """Verify that the exact text has a valid approval record.

        HARD RULE: No publication without matching Approval hash.
        """
        sha = compute_sha256(text)
        approval = self.db.get_approval_by_hash(sha)
        if not approval:
            raise UnapprovedContentError(
                f"Cannot publish: content hash {sha[:8]} has not been approved."
            )
        return approval
