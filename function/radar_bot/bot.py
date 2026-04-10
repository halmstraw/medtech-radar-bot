"""
bot.py — core conversation handler
Receives a Telegram update, manages conversation state, calls Claude,
raises GitHub PR when confirmed.

Conversation states:
  idle               — waiting for a new suggestion
  pending_confirmation — recommendation shown, waiting for yes/correction/cancel
"""

import logging
import os
import re
from typing import Any

import requests as http_requests

from .github import get_radar_context, raise_pr
from .claude import research_and_recommend
from .telegram import send_message, get_chat_id, get_text, get_user_id
from .state import get_state, set_state, clear_state

logger = logging.getLogger(__name__)

# Allowlist of Telegram user IDs permitted to use the bot
ALLOWED_USER_IDS = {
    7773419043,  # Tim
}

CONFIRM_PHRASES = {"yes", "ok", "go", "raise pr", "submit", "confirm", "looks good"}
CANCEL_PHRASES = {"no", "cancel", "stop", "abort"}

URL_PATTERN = re.compile(r'https?://\S+|www\.\S+|\S+\.\S+/\S*', re.IGNORECASE)


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

    if user_id not in ALLOWED_USER_IDS:
        logger.info("Rejected user %s — not in allowlist", user_id)
        send_message(chat_id, "Sorry, this bot is private.")
        return

    logger.info("Message from user %s: %s", user_id, text[:100])

    text_lower = text.strip().lower()
    state = get_state(chat_id)

    # --- Cancel always works regardless of state ---
    if text_lower in CANCEL_PHRASES:
        clear_state(chat_id)
        send_message(chat_id, "Cancelled. Send me a technology to evaluate whenever you're ready.")
        return

    # --- Pending confirmation state ---
    if state and state.get("state") == "pending_confirmation":

        if text_lower in CONFIRM_PHRASES:
            _raise_pr(chat_id, state)
        else:
            # Treat as a correction — re-research with the feedback
            _handle_suggestion(chat_id, state["suggestion"], correction=text, url_content=state.get("url_content"))
        return

    # --- Idle state — new suggestion ---
    _handle_suggestion(chat_id, text)


def _handle_suggestion(chat_id: int, text: str, correction: str | None = None, url_content: str | None = None) -> None:
    """Research a technology and recommend placement."""

    # Detect URL in the suggestion if not already fetched
    if url_content is None:
        url = _extract_url(text)
        if url:
            url_content = _fetch_url(url)
            if url_content:
                logger.info("Fetched URL content for: %s (%d chars)", url, len(url_content))

    send_message(chat_id, "On it — researching now...")

    try:
        radar_context = get_radar_context()
    except Exception as e:
        logger.error("Failed to fetch radar context: %s", e)
        send_message(chat_id, "Sorry, I couldn't fetch the current radar. Please try again.")
        return

    # Build the full suggestion string including any correction
    full_suggestion = text
    if correction:
        full_suggestion = f"{text}\n\nUser correction: {correction}"

    try:
        recommendation = research_and_recommend(
            suggestion=full_suggestion,
            radar_context=radar_context,
            url_content=url_content,
        )
    except Exception as e:
        logger.error("Claude API error: %s", e)
        send_message(chat_id, "Sorry, something went wrong with the research. Please try again.")
        return

    # Save state
    set_state(chat_id, {
        "state": "pending_confirmation",
        "suggestion": text,
        "url_content": url_content,
        "recommendation": recommendation,
    })

    reply = _format_recommendation(recommendation)
    send_message(chat_id, reply)


def _raise_pr(chat_id: int, state: dict) -> None:
    """Raise a GitHub PR for the pending recommendation."""
    rec = state["recommendation"]
    suggestion = state["suggestion"]

    send_message(chat_id, "Raising PR...")

    try:
        # Generate filename from title
        slug = re.sub(r"[^a-z0-9]+", "-", rec["title"].lower()).strip("-")
        filename = f"{slug}.md"
        pr_url = raise_pr(
            title=rec["title"],
            filename=filename,
            content=rec["entry_markdown"],
            suggestion=suggestion,
        )
        clear_state(chat_id)
        send_message(chat_id, f"PR raised: {pr_url}")
    except Exception as e:
        logger.error("Failed to raise PR: %s", e)
        send_message(chat_id, "Sorry, I couldn't raise the PR. Please try again.")


def _extract_url(text: str) -> str | None:
    """Extract the first URL from a message."""
    match = URL_PATTERN.search(text)
    if match:
        url = match.group(0)
        if not url.startswith("http"):
            url = "https://" + url
        return url
    return None


def _fetch_url(url: str) -> str | None:
    """Fetch and extract text content from a URL."""
    try:
        resp = http_requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        # Strip HTML tags crudely — good enough for Claude to read
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        # Truncate to avoid token bloat
        return text[:8000]
    except Exception as e:
        logger.warning("Failed to fetch URL %s: %s", url, e)
        return None


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
        "*Proposed entry:*",
        "```",
        rec["entry_markdown"],
        "```",
        "",
        "Reply *yes* to raise a PR, or tell me what to change.",
    ]
    return "\n".join(lines)
