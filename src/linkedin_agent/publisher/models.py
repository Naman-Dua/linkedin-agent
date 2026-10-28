"""Data models for LinkedIn publishing."""

from __future__ import annotations

from pydantic import BaseModel


class PublishResult(BaseModel):
    """Result of a publish operation."""

    urn: str
    url: str | None
    idempotency_key: str
    is_dry_run: bool = False
