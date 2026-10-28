"""Tests for LinkedIn publisher and gate integration."""

from pathlib import Path
from typing import Any

import httpx
import pytest

from linkedin_agent.approval.gate import ApprovalGate, UnapprovedContentError
from linkedin_agent.publisher.linkedin import LinkedInPublisher, LinkedInPublishError
from linkedin_agent.store.db import Database


def test_publish_blocked_without_approval(tmp_path: Path) -> None:
    db = Database(tmp_path / "pub_test.db")
    pub = LinkedInPublisher(db, access_token="mock_tok")

    # Attempting to publish without approving first raises UnapprovedContentError
    with pytest.raises(UnapprovedContentError):
        pub.publish_post(
            draft_id=1,
            repo="org/repo",
            text="Unapproved draft text here.",
            dry_run=True,
        )


def test_publish_dry_run_success(tmp_path: Path) -> None:
    db = Database(tmp_path / "pub_test.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="mock_tok")

    text = "Approved text ready for LinkedIn."
    draft = gate.register_draft(repo="org/repo", variant_no=1, text=text)
    gate.approve_draft(draft.id, channel="cli")

    result = pub.publish_post(draft_id=draft.id, repo="org/repo", text=text, dry_run=True)
    assert result.is_dry_run is True
    assert "dry_run" in result.urn
    assert result.idempotency_key is not None


def test_publish_live_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = Database(tmp_path / "pub_test.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="live_tok_123")

    text = "Live post announcing an open source project."
    draft = gate.register_draft(repo="org/repo", variant_no=1, text=text)
    gate.approve_draft(draft.id, channel="cli")

    def mock_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        assert "/v2/userinfo" in url
        req = httpx.Request("GET", url)
        return httpx.Response(200, json={"sub": "person_123"}, request=req)

    def mock_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        assert "/rest/posts" in url
        req = httpx.Request("POST", url)
        return httpx.Response(
            201,
            headers={"x-restli-id": "urn:li:share:987654321"},
            request=req,
        )

    monkeypatch.setattr(httpx.Client, "get", mock_get)
    monkeypatch.setattr(httpx.Client, "post", mock_post)

    result = pub.publish_post(draft_id=draft.id, repo="org/repo", text=text, dry_run=False)
    assert result.is_dry_run is False
    assert result.urn == "urn:li:share:987654321"
    assert result.url == "https://www.linkedin.com/feed/update/urn:li:share:987654321/"

    # Verify recorded in DB
    assert db.has_repo_been_posted("org/repo") is True

    # Test idempotency: second call returns existing record without re-sending
    monkeypatch.delattr(httpx.Client, "post")  # If it tries to send POST, it will error
    dup_result = pub.publish_post(draft_id=draft.id, repo="org/repo", text=text, dry_run=False)
    assert dup_result.urn == "urn:li:share:987654321"


def test_publish_live_expired_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    db = Database(tmp_path / "pub_test.db")
    gate = ApprovalGate(db)
    pub = LinkedInPublisher(db, access_token="expired_tok")

    text = "Post text."
    draft = gate.register_draft(repo="org/repo", variant_no=1, text=text)
    gate.approve_draft(draft.id, channel="cli")

    def mock_get(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("GET", url)
        return httpx.Response(401, json={"message": "Token expired"}, request=req)

    monkeypatch.setattr(httpx.Client, "get", mock_get)

    with pytest.raises(LinkedInPublishError, match="expired or unauthorized"):
        pub.publish_post(draft_id=draft.id, repo="org/repo", text=text, dry_run=False)
