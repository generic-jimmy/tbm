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


# Telegram Bot API method + multipart field name, by our internal 'kind'.
_UPLOAD_METHOD = {
    "photo": ("sendPhoto", "photo"),
    "video": ("sendVideo", "video"),
    "audio": ("sendAudio", "audio"),
    "voice": ("sendVoice", "voice"),
}


async def upload_media_to_storage(
    client: httpx.AsyncClient,
    token: str,
    storage_chat_id: int,
    data: bytes,
    filename: str,
    kind: str,
) -> Optional[tuple[int, str]]:
    """Upload raw media bytes (e.g. downloaded via Telethon) to the storage
    group, returning (storage_msg_id, storage_file_id) — a real Bot-API
    file_id, downloadable through the normal /api/files/{id}/download route.

    Used by the MTProto importer's optional "download media" mode: Telethon's
    internal file references aren't valid Bot API file_ids, so to make
    imported media downloadable the same way as live-polled media, we pull
    the bytes via MTProto once and re-upload them through the Bot API.
    """
    method, field = _UPLOAD_METHOD.get(kind, ("sendDocument", "document"))
    try:
        res = await client.post(
            f"https://api.telegram.org/bot{token}/{method}",
            data={"chat_id": storage_chat_id},
            files={field: (filename, data)},
            timeout=120.0,
        )
        d = res.json()
        if not d.get("ok"):
            logger.warning(f"Media re-upload failed: {d.get('description')}")
            return None
        result = d["result"]
        return result["message_id"], _extract_file_id(result) or ""
    except Exception as e:
        logger.error(f"Media re-upload error: {e}")
        return None
