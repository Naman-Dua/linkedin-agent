"""Tests for SQLite database storage."""

from pathlib import Path

from linkedin_agent.store.db import Database


def test_database_crud(tmp_path: Path) -> None:
    db_file = tmp_path / "test.db"
    db = Database(db_file)

    # Save draft
    draft_id = db.save_draft(
        repo="user/test-repo",
        variant_no=1,
        text="Hello world draft post",
        text_sha256="abc123sha",
        status="PENDING_APPROVAL",
    )
    assert draft_id == 1

    draft = db.get_draft(draft_id)
    assert draft is not None
    assert draft.repo == "user/test-repo"
    assert draft.text == "Hello world draft post"
    assert draft.status == "PENDING_APPROVAL"

    # Record approval
    approval_id = db.record_approval(draft_id, "abc123sha", channel="cli")
    assert approval_id == 1

    updated_draft = db.get_draft(draft_id)
    assert updated_draft is not None
    assert updated_draft.status == "APPROVED"

    approval = db.get_approval_by_hash("abc123sha")
    assert approval is not None
    assert approval.draft_id == draft_id

    # Record post
    post_id = db.record_post(
        draft_id=draft_id,
        linkedin_urn="urn:li:share:12345",
        url="https://linkedin.com/feed/update/12345",
        idempotency_key="idemp_1",
    )
    assert post_id == 1
    assert db.has_repo_been_posted("user/test-repo") is True

    # Retrieve post by idempotency key
    post = db.get_post_by_idempotency_key("idemp_1")
    assert post is not None
    assert post.linkedin_urn == "urn:li:share:12345"

    # Tokens meta
    db.save_token("linkedin", "access_tok_123", "2026-12-31T00:00:00Z")
    tok = db.get_token("linkedin")
    assert tok == ("access_tok_123", "2026-12-31T00:00:00Z")
