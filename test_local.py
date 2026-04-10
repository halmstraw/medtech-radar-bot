#!/usr/bin/env python3
"""
Local test harness — simulates a Telegram message without needing
a live webhook. Requires environment variables to be set.

Usage:
  export TELEGRAM_BOT_TOKEN=...
  export ANTHROPIC_API_KEY=...
  export GITHUB_TOKEN=...
  python test_local.py "Temporal for workflow orchestration"
"""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "function"))

from radar_bot.bot import handle_update

def simulate_message(text: str, user_id: int = 7773419043, chat_id: int = 7773419043):
    update = {
        "update_id": 99999999,
        "message": {
            "message_id": 1,
            "from": {
                "id": user_id,
                "is_bot": False,
                "first_name": "Test",
            },
            "chat": {
                "id": chat_id,
                "type": "private",
            },
            "date": 1234567890,
            "text": text,
        }
    }
    print(f"\n→ Simulating message: '{text}'\n")
    handle_update(update)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_local.py '<your suggestion>'")
        sys.exit(1)
    simulate_message(" ".join(sys.argv[1:]))
