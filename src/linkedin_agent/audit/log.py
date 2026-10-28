"""Append-only audit log for tracking all agent decisions, approvals, and publishes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from linkedin_agent.context.redaction import redact_text

AUDIT_LOG_DEFAULT = Path.cwd() / "audit.jsonl"


def audit_log(
    event: str,
    data: dict[str, Any] | None = None,
    log_file: Path | None = None,
) -> None:
    """Write an append-only JSONL entry for an event."""
    target_file = log_file or AUDIT_LOG_DEFAULT
    now = datetime.now(UTC).isoformat()

    # Redact sensitive values from log data
    safe_data: dict[str, Any] = {}
    if data:
        for k, v in data.items():
            if isinstance(v, str):
                safe_data[k] = redact_text(v)
            else:
                safe_data[k] = v

    record = {
        "timestamp": now,
        "event": event,
        "data": safe_data,
    }

    try:
        target_file.parent.mkdir(parents=True, exist_ok=True)
        with target_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        pass
