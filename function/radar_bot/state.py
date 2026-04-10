"""
state.py — conversation state via Azure Table Storage

Each conversation is keyed by Telegram chat_id.
State persists across Function instances and cold starts.

Table: RadarBotState
Partition key: "conversations"
Row key: str(chat_id)

States:
  idle               — no pending recommendation
  pending_confirmation — waiting for yes/no/correction
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)

TABLE_NAME = "RadarBotState"
PARTITION_KEY = "conversations"
STATE_TTL_HOURS = 24


def _get_table_client():
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    service = TableServiceClient.from_connection_string(conn_str)
    service.create_table_if_not_exists(TABLE_NAME)
    return service.get_table_client(TABLE_NAME)


def get_state(chat_id: int) -> dict[str, Any] | None:
    """Retrieve conversation state for a chat. Returns None if idle/expired."""
    try:
        client = _get_table_client()
        entity = client.get_entity(PARTITION_KEY, str(chat_id))

        # Check TTL
        created_at = datetime.fromisoformat(entity["created_at"])
        age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
        if age_hours > STATE_TTL_HOURS:
            logger.info("State expired for chat %s", chat_id)
            clear_state(chat_id)
            return None

        return json.loads(entity["data"])

    except ResourceNotFoundError:
        return None
    except Exception as e:
        logger.error("Failed to get state for chat %s: %s", chat_id, e)
        return None


def set_state(chat_id: int, data: dict[str, Any]) -> None:
    """Store conversation state for a chat."""
    try:
        client = _get_table_client()
        entity = {
            "PartitionKey": PARTITION_KEY,
            "RowKey": str(chat_id),
            "data": json.dumps(data),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        client.upsert_entity(entity)
        logger.info("State saved for chat %s: %s", chat_id, data.get("state"))
    except Exception as e:
        logger.error("Failed to save state for chat %s: %s", chat_id, e)


def clear_state(chat_id: int) -> None:
    """Clear conversation state for a chat (return to idle)."""
    try:
        client = _get_table_client()
        client.delete_entity(PARTITION_KEY, str(chat_id))
        logger.info("State cleared for chat %s", chat_id)
    except ResourceNotFoundError:
        pass
    except Exception as e:
        logger.error("Failed to clear state for chat %s: %s", chat_id, e)
