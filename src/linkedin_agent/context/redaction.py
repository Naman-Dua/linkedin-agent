"""Security redaction filter to scrub secrets, credentials, and emails."""

import re

# Common patterns for tokens, keys, and credentials
PATTERNS = [
    # Private keys
    (
        re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"),
        "[REDACTED_PRIVATE_KEY]",
    ),
    # GitHub personal access tokens
    (
        re.compile(r"\b(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})\b"),
        "[REDACTED_GITHUB_TOKEN]",
    ),
    # Slack / generic bot tokens
    (re.compile(r"\bxox[baprs]-[a-zA-Z0-9-]{10,}\b"), "[REDACTED_TOKEN]"),
    # Generic bearer tokens & auth headers
    (re.compile(r"(?i)\bBearer\s+[a-zA-Z0-9\-._~+/]+=*"), "Bearer [REDACTED_TOKEN]"),
    # Generic key/secret assignments (e.g. api_key="...", password = '...')
    (
        re.compile(
            r"(?i)\b(api[_-]?key|key|secret|token|password|auth|passwd)\s*[:=]\s*['\"]?([a-zA-Z0-9\-_./+=]{4,})['\"]?"
        ),
        r"\1=[REDACTED_SECRET]",
    ),
    # Email addresses
    (re.compile(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b"), "[REDACTED_EMAIL]"),
]


def redact_text(text: str | None) -> str | None:
    """Scrub sensitive credentials, tokens, and emails from text."""
    if not text:
        return text

    sanitized = text
    for pattern, replacement in PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized
