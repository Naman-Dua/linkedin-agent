"""Tests for cryptographic approval gate and state transitions."""

from pathlib import Path

import pytest

from linkedin_agent.approval.gate import (
    ApprovalGate,
    UnapprovedContentError,
    compute_sha256,
)
from linkedin_agent.store.db import Database


def test_approval_gate_lifecycle(tmp_path: Path) -> None:
    db = Database(tmp_path / "gate_test.db")
    gate = ApprovalGate(db)

    text = "Building an offline Flutter app with SQLite."
    draft = gate.register_draft(repo="org/app", variant_no=1, text=text)

    # 1. Unapproved content CANNOT be published
    with pytest.raises(UnapprovedContentError):
        gate.verify_can_publish(text)

    # 2. Approve draft
    approval = gate.approve_draft(draft.id, channel="cli")
    assert approval.text_sha256 == compute_sha256(text)

    # 3. Now verified to publish
    verified = gate.verify_can_publish(text)
    assert verified.text_sha256 == approval.text_sha256

    # 4. Modifying even one character invalidates approval
    mutated_text = text + " Extra claim!"
    with pytest.raises(UnapprovedContentError):
        gate.verify_can_publish(mutated_text)

    # 5. Editing creates new draft requiring fresh approval
    edited_draft = gate.edit_draft(draft.id, mutated_text)
    assert edited_draft.parent_draft_id == draft.id
    assert edited_draft.status == "PENDING_APPROVAL"

    # Prior approval DOES NOT apply to edited text
    with pytest.raises(UnapprovedContentError):
        gate.verify_can_publish(mutated_text)

    # Approving edited draft enables publishing mutated text
    gate.approve_draft(edited_draft.id, channel="cli")
    verified_edited = gate.verify_can_publish(mutated_text)
    assert verified_edited.text_sha256 == compute_sha256(mutated_text)
