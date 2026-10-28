"""Tests for LinkedIn OAuth helper functions."""

from typing import Any

import httpx
import pytest

from linkedin_agent.publisher.oauth import (
    exchange_code_for_token,
    get_authorization_url,
)


def test_get_authorization_url() -> None:
    url = get_authorization_url(
        client_id="my_client_id",
        redirect_uri="http://localhost:8080/callback",
        state="xyz123",
    )
    assert "https://www.linkedin.com/oauth/v2/authorization" in url
    assert "client_id=my_client_id" in url
    assert "w_member_social" in url
    assert "state=xyz123" in url


def test_exchange_code_for_token_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_post(self: httpx.Client, url: str, **kwargs: Any) -> httpx.Response:
        req = httpx.Request("POST", url)
        return httpx.Response(
            200,
            json={"access_token": "tok_abc_123", "expires_in": 3600},
            request=req,
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)
    token, expires_in = exchange_code_for_token(
        code="code_123",
        client_id="cid",
        client_secret="sec",
        redirect_uri="http://localhost:8080/callback",
    )
    assert token == "tok_abc_123"
    assert expires_in == 3600
