"""
medtech-radar-bot — Azure Function entry point
Telegram webhook → Claude API → GitHub PR
"""

import json
import logging
import os

import azure.functions as func

from .bot import handle_update

logger = logging.getLogger(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger — receives Telegram webhook updates."""

    # Verify the request is from Telegram via secret token header
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if secret and req.headers.get("X-Telegram-Bot-Api-Secret-Token") != secret:
        logger.warning("Rejected request — invalid webhook secret")
        return func.HttpResponse(status_code=403)

    try:
        update = req.get_json()
    except ValueError:
        return func.HttpResponse(status_code=400)

    try:
        handle_update(update)
    except Exception as e:
        logger.exception("Unhandled error processing update: %s", e)

    # Always return 200 to Telegram — otherwise it retries
    return func.HttpResponse(status_code=200)
