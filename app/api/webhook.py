"""Receives Telegram webhook updates (when WEBHOOK_BASE_URL is configured)."""
import hmac
import logging

from fastapi import APIRouter, Request

from app.config import get_settings
from app.webhook import webhook_secret_for

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.post("/{bot_hash}")
async def receive_webhook(bot_hash: str, request: Request):
    s = get_settings()
    expected = webhook_secret_for(bot_hash, s.secret_key)
    got = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")

    if not hmac.compare_digest(got, expected):
        # Don't leak *why* — just look like nothing's here.
        return {"ok": False}

    # Imported lazily to avoid a circular import (app.main constructs the
    # routers, which import this module, before bot_manager exists at
    # module scope elsewhere).
    from app.main import bot_manager

    worker = bot_manager.get_worker(bot_hash)
    if not worker:
        # Bot isn't running in this process (e.g. mid-restart). ACK with 200
        # anyway so Telegram doesn't back off / retry-storm the endpoint —
        # the update is simply dropped, same as it would be if the bot were
        # offline during a polling gap.
        logger.warning(f"Webhook hit for inactive bot {bot_hash[:8]}")
        return {"ok": True}

    payload = await request.json()
    await worker.handle_webhook_update(payload)
    return {"ok": True}
