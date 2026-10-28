"""Data models for SQLite store."""

from __future__ import annotations

from pydantic import BaseModel


class DraftRecord(BaseModel):
    """Database record for a generated draft."""

    id: int
    repo: str
    variant_no: int
    text: str
    text_sha256: str
    status: str
    created_at: str
    parent_draft_id: int | None = None


class ApprovalRecord(BaseModel):
    """Database record for an explicit user approval."""

    id: int
    draft_id: int
    text_sha256: str
    approved_at: str
    channel: str


class PostRecord(BaseModel):
    """Database record for a published LinkedIn post."""

    id: int
    draft_id: int
    linkedin_urn: str
    url: str | None
    posted_at: str
    idempotency_key: str
