"""Official LinkedIn Posts API publisher with hard approval check and idempotency."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import httpx

from linkedin_agent.approval.gate import ApprovalGate, compute_sha256
from linkedin_agent.audit.log import audit_log
from linkedin_agent.publisher.models import PublishResult
from linkedin_agent.store.db import Database

LINKEDIN_API_BASE = "https://api.linkedin.com"


class LinkedInPublishError(Exception):
    """Raised when publication to LinkedIn fails."""


class LinkedInPublisher:
    """Client for publishing approved posts to LinkedIn."""

    def __init__(
        self,
        db: Database,
        access_token: str | None = None,
        api_version: str | None = None,
        timeout: float = 20.0,
    ) -> None:
        self.db = db
        self.gate = ApprovalGate(db)
        self.timeout = timeout
        self.api_version = (
            api_version or os.getenv("LINKEDIN_VERSION") or "202601"
        )
        self._token = access_token

    def get_access_token(self) -> str:
        """Resolve valid access token from parameter, env, or database."""
        if self._token:
            return self._token
        env_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        if env_token:
            return env_token
        saved = self.db.get_token("linkedin")
        if saved:
            return saved[0]
        raise LinkedInPublishError(
            "No LinkedIn access token available. Run 'agent auth login' first."
        )

    def get_author_urn(self, token: str) -> str:
        """Fetch member author URN from userinfo endpoint."""
        url = f"{LINKEDIN_API_BASE}/v2/userinfo"
        headers = {"Authorization": f"Bearer {token}"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 401:
                    raise LinkedInPublishError("LinkedIn token is expired or unauthorized (401).")
                if resp.is_error:
                    raise LinkedInPublishError(
                        f"Failed to fetch userinfo ({resp.status_code}): {resp.text}"
                    )
                data = resp.json()
                sub = data.get("sub")
                if not sub:
                    raise LinkedInPublishError(f"Missing 'sub' identifier in userinfo: {data}")
                return f"urn:li:person:{sub}"
        except httpx.RequestError as exc:
            raise LinkedInPublishError(f"Network error calling userinfo: {exc}") from exc

    def create_idempotency_key(self, repo: str, text: str) -> str:
        """Generate unique idempotency key based on repo and text hash."""
        sha = compute_sha256(text)
        return hashlib.sha256(f"{repo}:{sha}".encode()).hexdigest()

    def publish_post(
        self,
        draft_id: int,
        repo: str,
        text: str,
        dry_run: bool = True,
        visibility: str = "PUBLIC",
    ) -> PublishResult:
        """Publish an approved post to LinkedIn under strict gate verification."""
        # 1. HARD INVARIANT: Cryptographic approval check
        approval = self.gate.verify_can_publish(text)

        # 2. Idempotency duplicate check
        idempotency_key = self.create_idempotency_key(repo, text)
        existing = self.db.get_post_by_idempotency_key(idempotency_key)
        if existing:
            return PublishResult(
                urn=existing.linkedin_urn,
                url=existing.url,
                idempotency_key=idempotency_key,
                is_dry_run=False,
            )

        # 3. Dry Run Handling
        if dry_run:
            mock_urn = f"urn:li:share:dry_run_{approval.text_sha256[:8]}"
            audit_log(
                "post_published_dry_run",
                {
                    "draft_id": draft_id,
                    "repo": repo,
                    "sha256": approval.text_sha256,
                    "idempotency_key": idempotency_key,
                },
            )
            return PublishResult(
                urn=mock_urn,
                url=None,
                idempotency_key=idempotency_key,
                is_dry_run=True,
            )

        # 4. Live Publish to LinkedIn REST API
        token = self.get_access_token()
        author_urn = self.get_author_urn(token)

        headers = {
            "Authorization": f"Bearer {token}",
            "Linkedin-Version": self.api_version,
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "author": author_urn,
            "commentary": text,
            "visibility": visibility,
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        url = f"{LINKEDIN_API_BASE}/rest/posts"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 401:
                    raise LinkedInPublishError(
                        "LinkedIn token expired or unauthorized during publish."
                    )
                if resp.is_error:
                    raise LinkedInPublishError(
                        f"LinkedIn publish API error ({resp.status_code}): {resp.text}"
                    )

                # Post URN is returned in x-restli-id header
                urn = resp.headers.get("x-restli-id", "")
                if not urn:
                    # Fallback to response body ID if present
                    urn = str(resp.json().get("id", f"urn:li:share:{approval.text_sha256[:8]}"))

                post_url = f"https://www.linkedin.com/feed/update/{urn}/"
                self.db.record_post(
                    draft_id=draft_id,
                    linkedin_urn=urn,
                    url=post_url,
                    idempotency_key=idempotency_key,
                )
                audit_log(
                    "post_published_live",
                    {
                        "draft_id": draft_id,
                        "repo": repo,
                        "urn": urn,
                        "url": post_url,
                        "sha256": approval.text_sha256,
                    },
                )
                return PublishResult(
                    urn=urn,
                    url=post_url,
                    idempotency_key=idempotency_key,
                    is_dry_run=False,
                )
        except httpx.RequestError as exc:
            raise LinkedInPublishError(f"Network error while publishing post: {exc}") from exc
