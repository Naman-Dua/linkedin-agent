"""Tests for security redaction filter."""

from linkedin_agent.context.redaction import redact_text


def test_redact_github_pat() -> None:
    text = "Secret token is ghp_123456789012345678901234567890123456 in use."
    redacted = redact_text(text)
    assert "[REDACTED_GITHUB_TOKEN]" in redacted
    assert "ghp_" not in redacted


def test_redact_generic_secret() -> None:
    text = "api_key='sk_live_1234567890' and password = 'my_super_secret_pwd'"
    redacted = redact_text(text)
    assert "api_key=[REDACTED_SECRET]" in redacted
    assert "password=[REDACTED_SECRET]" in redacted
    assert "sk_live" not in redacted


def test_redact_email() -> None:
    text = "Contact me at dev.author@example.com for questions."
    redacted = redact_text(text)
    assert "[REDACTED_EMAIL]" in redacted
    assert "dev.author@example.com" not in redacted


def test_redact_private_key() -> None:
    text = (
        "Key:\n"
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0\n"
        "-----END RSA PRIVATE KEY-----\n"
        "Done"
    )
    redacted = redact_text(text)
    assert "[REDACTED_PRIVATE_KEY]" in redacted
    assert "MIIEow" not in redacted


def test_redact_bearer_token() -> None:
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    redacted = redact_text(text)
    assert "Bearer [REDACTED_TOKEN]" in redacted
    assert "eyJhbGci" not in redacted
