"""Tests for append-only audit logging."""

import json
from pathlib import Path

from linkedin_agent.audit.log import audit_log


def test_audit_log_redaction_and_append(tmp_path: Path) -> None:
    log_file = tmp_path / "audit.jsonl"
    fake_token = "ghp_123456789012345678901234567890123456"

    audit_log("test_event", {"token": fake_token, "note": "ok"}, log_file=log_file)
    audit_log("second_event", {"status": "success"}, log_file=log_file)

    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2

    first = json.loads(lines[0])
    assert first["event"] == "test_event"
    assert "[REDACTED_GITHUB_TOKEN]" in first["data"]["token"]
    assert "ghp_" not in first["data"]["token"]

    second = json.loads(lines[1])
    assert second["event"] == "second_event"
    assert second["data"]["status"] == "success"
