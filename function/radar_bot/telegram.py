"""
telegram.py — Telegram Bot API helpers
"""

import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)


def _bot_url(method: str) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message(chat_id: int, text: str) -> None:
    """Send a message to a Telegram chat."""
    try:
        resp = requests.post(
            _bot_url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)


def get_chat_id(message: dict[str, Any]) -> int:
    return message["chat"]["id"]


def get_user_id(message: dict[str, Any]) -> int:
    return message["from"]["id"]


def get_text(message: dict[str, Any]) -> str:
    return message.get("text", "").strip()
