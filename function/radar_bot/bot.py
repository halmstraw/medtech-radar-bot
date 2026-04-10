"""
bot.py — core conversation handler
Receives a Telegram update, manages the conversation, calls Claude,
raises GitHub PR when confirmed.
"""

import logging
import os
from typing import Any

from .github import get_radar_context, raise_pr
from .claude import research_and_recommend, generate_entry
from .telegram import send_message, get_chat_id, get_text, get_user_id

logger = logging.getLogger(__name__)

# Allowlist of Telegram user IDs permitted to use the bot
ALLOWED_USER_IDS = {
    7773419043,  # Tim
}

# Trigger phrases that confirm a PR should be raised
CONFIRM_PHRASES = {"yes", "ok", "go", "raise pr", "submit", "confirm", "looks good"}
CANCEL_PHRASES = {"no", "cancel", "stop", "abort"}


def handle_update(update: dict[str, Any]) -> None:
    """Entry point for all incoming Telegram updates."""

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    user_id = get_user_id(message)
    chat_id = get_chat_id(message)
    text = get_text(message)

    if not text:
        return

    # Access control
    if user_id not in ALLOWED_USER_IDS:
        logger.info("Rejected user %s — not in allowlist", user_id)
        send_message(chat_id, "Sorry, this bot is private.")
        return

    logger.info("Message from user %s: %s", user_id, text[:100])

    # Detect confirmation of a pending recommendation
    text_lower = text.strip().lower()

    if text_lower in CANCEL_PHRASES:
        send_message(chat_id, "Cancelled. Send me another technology to evaluate whenever you're ready.")
        return

    if text_lower in CONFIRM_PHRASES:
        send_message(chat_id, "Got it — let me know which technology this is for, or send me the full suggestion again.")
        return

    # Main flow — treat message as a new technology suggestion
    _handle_suggestion(chat_id, text)


def _handle_suggestion(chat_id: int, text: str) -> None:
    """Research a technology suggestion and recommend quadrant/ring."""

    send_message(chat_id, "On it — researching now...")

    # Fetch current radar context from GitHub
    try:
        radar_context = get_radar_context()
    except Exception as e:
        logger.error("Failed to fetch radar context: %s", e)
        send_message(chat_id, "Sorry, I couldn't fetch the current radar. Please try again.")
        return

    # Call Claude to research and recommend
    try:
        recommendation = research_and_recommend(text, radar_context)
    except Exception as e:
        logger.error("Claude API error: %s", e)
        send_message(chat_id, "Sorry, something went wrong with the research. Please try again.")
        return

    # Send recommendation back to user
    reply = _format_recommendation(recommendation)
    send_message(chat_id, reply)

    # Store pending state in the recommendation for follow-up
    # In stateless v1, we embed the draft entry in the message and
    # ask the user to confirm or adjust in their next message.
    # The next message re-enters handle_update — if it looks like a
    # confirmation we ask them to resend the full suggestion to commit.
    # For v1 this is good enough; v2 adds Cosmos DB for proper state.


def _format_recommendation(rec: dict) -> str:
    """Format a Claude recommendation for Telegram."""
    lines = [
        f"*{rec['title']}*",
        "",
        f"*Quadrant:* {rec['quadrant']}",
        f"*Ring:* {rec['ring']}",
        "",
        f"*Reasoning:* {rec['reasoning']}",
        "",
        f"*Proposed entry:*",
        "```",
        rec["entry_markdown"],
        "```",
        "",
        "Reply *yes* to raise a PR, or tell me what to change.",
    ]
    return "\n".join(lines)
