"""
tests/test_bot.py — unit tests for bot.py logic
No API keys or external calls needed.
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "function"))


class TestAllowlist:
    def test_allowed_user_passes(self):
        from radar_bot.telegram import get_user_id, get_chat_id, get_text
        message = {
            "message_id": 1,
            "from": {"id": 7773419043, "is_bot": False, "first_name": "Tim"},
            "chat": {"id": 7773419043, "type": "private"},
            "date": 1234567890,
            "text": "Temporal workflow engine",
        }
        assert get_user_id(message) == 7773419043
        assert get_chat_id(message) == 7773419043
        assert get_text(message) == "Temporal workflow engine"

    def test_unknown_user_rejected(self):
        from radar_bot.bot import ALLOWED_USER_IDS
        assert 99999999 not in ALLOWED_USER_IDS

    def test_known_user_allowed(self):
        from radar_bot.bot import ALLOWED_USER_IDS
        assert 7773419043 in ALLOWED_USER_IDS


class TestCancelPhrases:
    def test_cancel_phrases_present(self):
        from radar_bot.bot import CANCEL_PHRASES
        assert "cancel" in CANCEL_PHRASES
        assert "no" in CANCEL_PHRASES

    def test_confirm_phrases_present(self):
        from radar_bot.bot import CONFIRM_PHRASES
        assert "yes" in CONFIRM_PHRASES
        assert "ok" in CONFIRM_PHRASES


class TestWebhookEntry:
    def test_no_message_returns_early(self):
        """Updates with no message field should be handled gracefully."""
        from radar_bot.bot import handle_update
        # Should not raise
        handle_update({"update_id": 1})

    def test_empty_text_returns_early(self):
        from radar_bot.bot import handle_update
        with patch("radar_bot.bot.send_message") as mock_send:
            handle_update({
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "from": {"id": 7773419043, "is_bot": False, "first_name": "Tim"},
                    "chat": {"id": 7773419043, "type": "private"},
                    "date": 1234567890,
                    "text": "",
                }
            })
            mock_send.assert_not_called()

    def test_unknown_user_gets_rejection(self):
        from radar_bot.bot import handle_update
        with patch("radar_bot.bot.send_message") as mock_send:
            handle_update({
                "update_id": 1,
                "message": {
                    "message_id": 1,
                    "from": {"id": 99999999, "is_bot": False, "first_name": "Hacker"},
                    "chat": {"id": 99999999, "type": "private"},
                    "date": 1234567890,
                    "text": "Temporal",
                }
            })
            mock_send.assert_called_once()
            assert "private" in mock_send.call_args[0][1].lower()
