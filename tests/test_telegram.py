"""Tests for Telegram bot approval channel."""

from pathlib import Path
from unittest.mock import MagicMock

from linkedin_agent.approval.telegram import TelegramApprovalBot
from linkedin_agent.store.db import Database
from linkedin_agent.store.models import DraftRecord


def test_telegram_authorization_check(tmp_path: Path) -> None:
    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    # Matching chat
    valid_update = MagicMock()
    valid_update.effective_chat.id = 12345678
    assert bot.is_authorized(valid_update) is True

    # Unauthorized attacker chat
    evil_update = MagicMock()
    evil_update.effective_chat.id = 99999999
    assert bot.is_authorized(evil_update) is False

    # Empty chat
    none_update = MagicMock()
    none_update.effective_chat = None
    assert bot.is_authorized(none_update) is False


def test_telegram_format_draft_message(tmp_path: Path) -> None:
    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    draft = DraftRecord(
        id=1,
        repo="user/cool-app",
        variant_no=1,
        text="A post about offline-first design.",
        text_sha256="abcd1234efgh",
        status="PENDING_APPROVAL",
        created_at="2026-10-28T00:00:00Z",
    )
    msg = bot.format_draft_message(draft)
    assert "Draft Variant 1 for user/cool-app" in msg
    assert "A post about offline-first design." in msg
    assert "abcd1234ef" in msg


def test_telegram_expiry_alert(tmp_path: Path) -> None:
    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    # No token
    assert bot.check_token_expiry_alert() is None

    # Token expiring in 3 days
    from datetime import UTC, datetime, timedelta

    exp = (datetime.now(UTC) + timedelta(days=3)).isoformat()
    db.save_token("linkedin", "tok_exp", exp)
    alert = bot.check_token_expiry_alert()
    assert alert is not None
    assert "expires in 3 days" in alert

    # Token expiring in 30 days
    safe_exp = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    db.save_token("linkedin", "tok_safe", safe_exp)
    assert bot.check_token_expiry_alert() is None
