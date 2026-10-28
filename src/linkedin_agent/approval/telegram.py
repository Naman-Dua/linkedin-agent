"""Telegram bot approval channel with inline buttons and security chat allowlist."""

from __future__ import annotations

import html
import os
from datetime import UTC, datetime
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from linkedin_agent.approval.gate import ApprovalGate
from linkedin_agent.audit.log import audit_log
from linkedin_agent.drafter.models import DraftVariant
from linkedin_agent.store.db import Database
from linkedin_agent.store.models import DraftRecord


class TelegramApprovalBot:
    """Telegram bot interface for reviewing, approving, and editing drafts."""

    def __init__(
        self,
        db: Database,
        bot_token: str | None = None,
        allowed_chat_id: str | int | None = None,
    ) -> None:
        self.db = db
        self.gate = ApprovalGate(db)
        self.token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        raw_chat_id = allowed_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.allowed_chat_id = str(raw_chat_id) if raw_chat_id else None
        # Track pending edit states: chat_id -> draft_id
        self._pending_edits: dict[str, int] = {}

    def is_authorized(self, update: Update) -> bool:
        """Enforce strict chat ID allowlist."""
        if not update.effective_chat or not self.allowed_chat_id:
            return False
        return str(update.effective_chat.id) == self.allowed_chat_id

    def format_draft_message(self, draft: DraftRecord, variant: DraftVariant | None = None) -> str:
        """Format a clean markdown message for Telegram."""
        safe_text = html.escape(draft.text)
        safe_repo = html.escape(draft.repo)
        lines = [
            f"<b>Draft Variant {draft.variant_no} for {safe_repo}</b>",
            "",
            safe_text,
            "",
            f"<code>SHA256: {draft.text_sha256[:10]}...</code>",
        ]
        if variant and variant.warnings:
            lines.append("\n<b>Warnings:</b>")
            for w in variant.warnings:
                lines.append(f"⚠ {html.escape(w)}")
        return "\n".join(lines)

    def get_approval_keyboard(self, draft_id: int) -> InlineKeyboardMarkup:
        """Generate inline keyboard for approval actions."""
        keyboard = [
            [
                InlineKeyboardButton("✓ Approve", callback_data=f"approve_{draft_id}"),
                InlineKeyboardButton("✏ Edit", callback_data=f"edit_{draft_id}"),
            ],
            [
                InlineKeyboardButton("🔄 Regenerate", callback_data=f"regen_{draft_id}"),
                InlineKeyboardButton("✕ Skip", callback_data=f"skip_{draft_id}"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)

    async def handle_callback(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Process inline button selections."""
        query = update.callback_query
        if not query or not self.is_authorized(update):
            if query:
                await query.answer("Unauthorized.", show_alert=True)
            return

        await query.answer()
        data = query.data or ""
        action, _, draft_id_str = data.partition("_")

        try:
            draft_id = int(draft_id_str)
        except ValueError:
            return

        draft = self.db.get_draft(draft_id)
        if not draft:
            await query.edit_message_text("Error: Draft not found in database.")
            return

        chat_id = str(update.effective_chat.id) if update.effective_chat else ""

        if action == "approve":
            approval = self.gate.approve_draft(draft_id, channel="telegram")
            audit_log(
                "draft_approved",
                {
                    "draft_id": draft_id,
                    "repo": draft.repo,
                    "sha256": approval.text_sha256,
                    "channel": "telegram",
                },
            )
            safe_text = html.escape(draft.text)
            await query.edit_message_text(
                f"✓ <b>Draft #{draft_id} Approved!</b>\n\n{safe_text}\n\n"
                f"<code>Hash: {approval.text_sha256[:10]}</code>",
                parse_mode="HTML",
            )

        elif action == "edit":
            self._pending_edits[chat_id] = draft_id
            await query.message.reply_text(  # type: ignore[union-attr]
                f"Please reply with the new text for Draft #{draft_id}:"
            )

        elif action == "skip":
            self.db.update_draft_status(draft_id, "SKIPPED")
            audit_log("draft_skipped", {"draft_id": draft_id, "repo": draft.repo})
            await query.edit_message_text(f"✕ Draft #{draft_id} was skipped.")

        elif action == "regen":
            self.db.update_draft_status(draft_id, "REGENERATED")
            audit_log("draft_regenerate_requested", {"draft_id": draft_id, "repo": draft.repo})
            await query.edit_message_text(f"🔄 Regeneration requested for Draft #{draft_id}.")

    async def handle_reply_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Process text replies to handle draft edits."""
        if not self.is_authorized(update) or not update.message or not update.message.text:
            return

        chat_id = str(update.effective_chat.id) if update.effective_chat else ""
        draft_id = self._pending_edits.pop(chat_id, None)

        if not draft_id:
            return

        new_text = update.message.text.strip()
        new_draft = self.gate.edit_draft(draft_id, new_text)
        audit_log(
            "draft_edited",
            {
                "original_draft_id": draft_id,
                "new_draft_id": new_draft.id,
                "new_sha256": new_draft.text_sha256,
                "channel": "telegram",
            },
        )

        safe_new_text = html.escape(new_draft.text)
        msg = (
            f"<b>Updated Draft #{new_draft.id} (Prior approval invalidated)</b>\n\n"
            f"{safe_new_text}\n\n<code>SHA256: {new_draft.text_sha256[:10]}...</code>"
        )
        keyboard = self.get_approval_keyboard(new_draft.id)
        await update.message.reply_text(msg, parse_mode="HTML", reply_markup=keyboard)

    def check_token_expiry_alert(self) -> str | None:
        """Check if LinkedIn access token is close to expiry (T-7 days)."""
        tok = self.db.get_token("linkedin")
        if not tok:
            return None

        _, expires_at_str = tok
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            seconds = (expires_at - datetime.now(UTC)).total_seconds()
            days = max(0, round(seconds / 86400))
            if days <= 7:
                return (
                    f"⚠ Alert: LinkedIn token expires in {days} days! "
                    "Re-auth with 'agent auth login'."
                )
        except Exception:
            pass
        return None

    def build_application(self) -> Application[Any, Any, Any, Any, Any, Any]:
        """Configure python-telegram-bot application with handlers."""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not configured.")

        app = Application.builder().token(self.token).build()
        app.add_handler(CallbackQueryHandler(self.handle_callback))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_reply_message)
        )
        return app
