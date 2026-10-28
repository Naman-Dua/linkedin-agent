"""Hardening and invariant verification tests.

Validates all 6 non-negotiable checklist criteria required before disabling DRY_RUN.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from linkedin_agent.approval.gate import (
    ApprovalGate,
    UnapprovedContentError,
    compute_sha256,
)
from linkedin_agent.audit.log import audit_log
from linkedin_agent.context.models import CommitInfo, ProjectContext
from linkedin_agent.drafter.claims_check import audit_variant_claims
from linkedin_agent.drafter.models import ClaimItem, DraftVariant
from linkedin_agent.publisher.linkedin import LinkedInPublisher, LinkedInPublishError
from linkedin_agent.store.db import Database


def test_checklist_1_publish_blocked_without_approval(tmp_path: Path) -> None:
    """Checklist item 1: Publish blocked without approval."""
    db = Database(tmp_path / "hard1.db")
    pub = LinkedInPublisher(db, access_token="test_tok")

    text = "Draft content that has never been approved."
    with pytest.raises(UnapprovedContentError, match="has not been approved"):
        pub.publish_post(draft_id=1, repo="user/repo", text=text, dry_run=False)


def test_checklist_2_publish_blocked_after_edit_until_reapproved(tmp_path: Path) -> None:
    """Checklist item 2: Publish blocked after edit until re-approved."""
    db = Database(tmp_path / "hard2.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="test_tok")

    original_text = "Original approved post."
    draft = gate.register_draft("user/repo", 1, original_text)
    gate.approve_draft(draft.id)

    # Modifying the text creates a new draft in PENDING_APPROVAL
    edited_text = "Original approved post with additions."
    edited_draft = gate.edit_draft(draft.id, edited_text)

    # Attempting to publish the edited text fails because its hash is not approved
    with pytest.raises(UnapprovedContentError):
        pub.publish_post(
            draft_id=edited_draft.id,
            repo="user/repo",
            text=edited_text,
            dry_run=False,
        )

    # Once re-approved, it succeeds
    gate.approve_draft(edited_draft.id)
    # verify_can_publish now passes
    assert gate.verify_can_publish(edited_text).text_sha256 == compute_sha256(edited_text)


def test_checklist_3_retry_does_not_double_post(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Checklist item 3: Retry doesn't double-post (idempotency key protection)."""
    db = Database(tmp_path / "hard3.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="live_tok")

    text = "Idempotent announcement post."
    draft = gate.register_draft("user/repo", 1, text)
    gate.approve_draft(draft.id)

    def mock_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"sub": "author_id_1"}, request=req)

    call_count = 0

    def mock_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        req = httpx.Request("POST", url)
        return httpx.Response(201, headers={"x-restli-id": "urn:li:share:111"}, request=req)

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    monkeypatch.setattr(httpx.Client, "post", mock_post)

    # First publish: calls API
    res1 = pub.publish_post(draft_id=draft.id, repo="user/repo", text=text, dry_run=False)
    assert res1.urn == "urn:li:share:111"
    assert call_count == 1

    # Second publish: idempotency cache hit, no HTTP call
    res2 = pub.publish_post(draft_id=draft.id, repo="user/repo", text=text, dry_run=False)
    assert res2.urn == "urn:li:share:111"
    assert call_count == 1


def test_checklist_4_secrets_never_appear_in_logs(tmp_path: Path) -> None:
    """Checklist item 4: Secrets never appear in logs."""
    log_file = tmp_path / "audit.jsonl"
    secret_pat = "ghp_111122223333444455556666777788889999"
    email = "leaked.dev@company.com"

    audit_log(
        "draft_created",
        {
            "repo": "user/repo",
            "token": secret_pat,
            "contact": email,
            "raw_text": f"Connecting with token {secret_pat} and email {email}",
        },
        log_file=log_file,
    )

    log_content = log_file.read_text(encoding="utf-8")
    assert secret_pat not in log_content
    assert email not in log_content
    assert "[REDACTED_GITHUB_TOKEN]" in log_content
    assert "[REDACTED_EMAIL]" in log_content

    # Parse and verify JSON validity
    record = json.loads(log_content.strip())
    assert record["event"] == "draft_created"


def test_checklist_5_unsupported_claims_are_flagged() -> None:
    """Checklist item 5: Unsupported claims are flagged."""
    ctx = ProjectContext(
        repo="user/minimal-repo",
        description="A tiny CLI utility",
        languages=["Python"],
        topics=["cli"],
        stars=3,
        last_push="2026-10-25",
        recent_commits=[CommitInfo(sha="1234567", msg="init commit", date="2026-10-25")],
        readme_excerpt="A simple script.",
    )

    variant = DraftVariant(
        angle="problem-solution",
        text="This utility handled 10M requests and raised $5M in seed funding.",
        hashtags=["#cli"],
        claims=[
            ClaimItem(claim="Raised venture capital", source="invented"),
            ClaimItem(claim="Handles enterprise cloud traffic", source="invented"),
        ],
    )

    warnings = audit_variant_claims(variant, ctx)
    assert any("10M" in w or "5M" in w for w in warnings)
    assert any("venture capital" in w or "enterprise" in w for w in warnings)


def test_checklist_6_expired_token_clear_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Checklist item 6: Expired token → clear error, no crash."""
    db = Database(tmp_path / "hard6.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="expired_token")

    text = "Valid text."
    draft = gate.register_draft("user/repo", 1, text)
    gate.approve_draft(draft.id)

    def mock_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(401, json={"status": 401, "message": "Expired token"}, request=req)

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    with pytest.raises(LinkedInPublishError) as exc_info:
        pub.publish_post(draft_id=draft.id, repo="user/repo", text=text, dry_run=False)

    assert "expired or unauthorized" in str(exc_info.value).lower()
