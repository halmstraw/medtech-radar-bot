import json
import logging
import os

import azure.functions as func

from .bot import handle_update

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="webhook", methods=["POST"])
def telegram_webhook(req: func.HttpRequest) -> func.HttpResponse:
    try:
        update = req.get_json()
    except ValueError:
        logging.warning("Invalid JSON received")
        return func.HttpResponse("Bad Request", status_code=400)

    try:
        handle_update(update)
    except Exception as e:
        logging.exception("Unhandled error in handle_update: %s", e)

    # Always return 200 — Telegram will retry on non-200
    return func.HttpResponse("OK", status_code=200)
