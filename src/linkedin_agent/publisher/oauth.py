"""LinkedIn OAuth 2.0 flow with local callback server."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

from linkedin_agent.store.db import Database

AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Temporary local HTTP handler to capture OAuth redirect."""

    auth_code: str | None = None
    auth_state: str | None = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            OAuthCallbackHandler.auth_state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = b"<h1>Authentication successful!</h1><p>You can close this window.</p>"
            self.wfile.write(msg)
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authentication failed</h1>")

    def log_message(self, format: str, *args: object) -> None:
        # Silence default console logging
        pass


def get_authorization_url(
    client_id: str,
    redirect_uri: str,
    state: str,
) -> str:
    """Construct LinkedIn authorization URL with requested scopes."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "openid profile w_member_social",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> tuple[str, int]:
    """Exchange authorization code for access token."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(TOKEN_URL, data=data)
        if resp.is_error:
            raise RuntimeError(f"Failed to exchange token ({resp.status_code}): {resp.text}")
        payload = resp.json()
        token = str(payload["access_token"])
        expires_in = int(payload.get("expires_in", 5184000))  # Default ~60 days
        return token, expires_in


def run_oauth_flow(
    db: Database,
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
    port: int = 8080,
) -> str:
    """Run interactive OAuth flow on localhost."""
    cid = client_id or os.getenv("LINKEDIN_CLIENT_ID")
    sec = client_secret or os.getenv("LINKEDIN_CLIENT_SECRET")
    red = redirect_uri or os.getenv("LINKEDIN_REDIRECT_URI") or f"http://localhost:{port}/callback"

    if not cid or not sec:
        raise ValueError("Missing LINKEDIN_CLIENT_ID or LINKEDIN_CLIENT_SECRET in environment.")

    state = secrets.token_hex(16)
    auth_url = get_authorization_url(cid, red, state)

    print("\nPlease visit this URL to authenticate with LinkedIn:\n")
    print(auth_url)
    print(f"\nWaiting for callback on port {port}...")

    server = HTTPServer(("localhost", port), OAuthCallbackHandler)
    while OAuthCallbackHandler.auth_code is None:
        server.handle_request()

    code = OAuthCallbackHandler.auth_code
    returned_state = OAuthCallbackHandler.auth_state

    if returned_state != state:
        raise ValueError("CSRF State mismatch in OAuth callback!")

    token, expires_in = exchange_code_for_token(code, cid, sec, red)
    expires_at = (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat()

    db.save_token("linkedin", token, expires_at)
    return token
