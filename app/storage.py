"""Forward received files to the Telegram Storage Group."""
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)


async def forward_to_storage(
    client: httpx.AsyncClient,
    token: str,
    storage_chat_id: int,
    from_chat_id: int,
    message_id: int,
) -> Optional[tuple[int, str]]:
    """
    Forward a message to the storage group.
    Returns (storage_msg_id, storage_file_id) or None on failure.
    """
    try:
        res = await client.post(
            f"https://api.telegram.org/bot{token}/forwardMessage",
            json={
                "chat_id":      storage_chat_id,
                "from_chat_id": from_chat_id,
                "message_id":   message_id,
            },
            timeout=15.0,
        )
        data = res.json()
        if not data.get("ok"):
            logger.warning(f"forwardMessage failed: {data.get('description')}")
            return None

        result = data["result"]
        storage_msg_id = result["message_id"]

        # Extract new file_id from the forwarded message
        storage_file_id = _extract_file_id(result)
        return storage_msg_id, storage_file_id

    except Exception as e:
        logger.error(f"Storage forward error: {e}")
        return None


def _extract_file_id(msg: dict) -> Optional[str]:
    for key in ("document", "video", "audio", "voice", "sticker", "video_note"):
        if key in msg:
            return msg[key]["file_id"]
    if "photo" in msg:
        return msg["photo"][-1]["file_id"]
    return None
