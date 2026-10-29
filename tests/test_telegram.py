"""Tests for Telegram bot approval channel."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from linkedin_agent.approval.telegram import TelegramApprovalBot
from linkedin_agent.drafter.models import DraftVariant
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


def test_telegram_format_draft_message_html_escaping(tmp_path: Path) -> None:
    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    draft = DraftRecord(
        id=1,
        repo="user/<tag>&project",
        variant_no=1,
        text="Check out <Component> & <Service> with a > b syntax!",
        text_sha256="abcd1234efgh",
        status="PENDING_APPROVAL",
        created_at="2026-10-28T00:00:00Z",
    )
    variant = DraftVariant(
        variant_no=1,
        angle="deep_dive",
        text=draft.text,
        warnings=["Unverified: <Metric> & claim"],
    )
    msg = bot.format_draft_message(draft, variant=variant)
    assert "&lt;Component&gt; &amp; &lt;Service&gt;" in msg
    assert "&lt;tag&gt;&amp;project" in msg
    assert "Unverified: &lt;Metric&gt; &amp; claim" in msg
    assert "<Component>" not in msg


@pytest.mark.asyncio
async def test_telegram_callback_and_reply_html_escaping(tmp_path: Path) -> None:
    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    # Seed draft
    draft_id = db.save_draft(
        repo="test/repo",
        variant_no=1,
        text="Release <v2.0> & new features",
        text_sha256="hash123",
        status="PENDING_APPROVAL",
    )

    # 1. Test handle_callback approve with HTML escaping
    update = MagicMock()
    update.effective_chat.id = 12345678
    update.callback_query = AsyncMock()
    update.callback_query.data = f"approve_{draft_id}"

    context = MagicMock()
    await bot.handle_callback(update, context)

    update.callback_query.edit_message_text.assert_called_once()
    called_msg = update.callback_query.edit_message_text.call_args[0][0]
    assert "&lt;v2.0&gt; &amp; new features" in called_msg
    assert "<v2.0>" not in called_msg

    # 2. Test handle_reply_message edit with HTML escaping
    bot._pending_edits["12345678"] = draft_id
    reply_update = MagicMock()
    reply_update.effective_chat.id = 12345678
    reply_update.message = AsyncMock()
    reply_update.message.text = "Edited: <v2.1> & patched bug"

    await bot.handle_reply_message(reply_update, context)

    reply_update.message.reply_text.assert_called_once()
    reply_msg = reply_update.message.reply_text.call_args[0][0]
    assert "&lt;v2.1&gt; &amp; patched bug" in reply_msg
    assert "<v2.1>" not in reply_msg


@pytest.mark.asyncio
async def test_telegram_handle_callback_duplicate_click_graceful(tmp_path: Path) -> None:
    from telegram.error import BadRequest

    db = Database(tmp_path / "tg_test.db")
    bot = TelegramApprovalBot(db, allowed_chat_id="12345678")

    draft_id = db.save_draft(
        repo="test/repo",
        variant_no=1,
        text="A valid post text",
        text_sha256="hash456",
        status="PENDING_APPROVAL",
    )

    update = MagicMock()
    update.effective_chat.id = 12345678
    update.callback_query = AsyncMock()
    update.callback_query.data = f"skip_{draft_id}"
    update.callback_query.edit_message_text.side_effect = BadRequest(
        "Message is not modified: content and markup are the same"
    )

    context = MagicMock()
    # Should not raise exception
    await bot.handle_callback(update, context)


