"""Compose — send text (with optional inline keyboard) or media messages."""
import json
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth import require_auth
from app.database import db
from app.crypto import decrypt_token
from app.config import get_settings

router = APIRouter(prefix="/api/send", tags=["send"])

TG = "https://api.telegram.org/bot"

# Media type → (Bot API method, multipart field name)
_MEDIA_METHOD = {
    "photo":    ("sendPhoto",    "photo"),
    "video":    ("sendVideo",    "video"),
    "audio":    ("sendAudio",    "audio"),
    "document": ("sendDocument", "document"),
}


async def _get_token(bot_hash: str) -> str:
    bot = await db.get_bot(bot_hash)
    if not bot:
        raise HTTPException(404, "Bot not found")
    return decrypt_token(bot["token_encrypted"], get_settings().secret_key)


async def _validate_chat(client: httpx.AsyncClient, token: str, chat_id: str):
    cr = await client.get(f"{TG}{token}/getChat", params={"chat_id": chat_id})
    cd = cr.json()
    if not cd.get("ok"):
        desc = cd.get("description", "Unknown error")
        if "not found" in desc.lower():
            desc += ("\n\n• User must send /start to the bot first\n"
                     "• Groups use negative IDs (e.g. -100123456)")
        raise HTTPException(400, desc)


class SendRequest(BaseModel):
    bot_hash:     str
    chat_id:      str
    text:         str
    parse_mode:   Optional[str] = None
    # {"inline_keyboard": [[{"text": "Visit", "url": "https://..."}], ...]}
    # Only URL buttons are supported for now — callback-data buttons would
    # need a callback_query handler in the bot worker, which isn't wired up.
    reply_markup: Optional[dict] = None


@router.post("")
async def send_message(body: SendRequest, _=Depends(require_auth)):
    token = await _get_token(body.bot_hash)

    async with httpx.AsyncClient(timeout=10.0) as client:
        await _validate_chat(client, token, body.chat_id)

        payload = {"chat_id": body.chat_id, "text": body.text}
        if body.parse_mode and body.parse_mode != "None":
            payload["parse_mode"] = body.parse_mode
        if body.reply_markup:
            payload["reply_markup"] = json.dumps(body.reply_markup)

        res = await client.post(f"{TG}{token}/sendMessage", json=payload)
        data = res.json()
        if not data.get("ok"):
            raise HTTPException(400, data.get("description", "Send failed"))
        return {"ok": True, "message_id": data["result"]["message_id"]}


@router.post("/media")
async def send_media(
    bot_hash:     str = Form(...),
    chat_id:      str = Form(...),
    media_type:   str = Form("document"),   # photo | video | audio | document
    caption:      str = Form(""),
    reply_markup: str = Form(""),           # JSON string, optional
    file:         UploadFile = File(...),
    _=Depends(require_auth),
):
    if media_type not in _MEDIA_METHOD:
        raise HTTPException(400, f"Unsupported media_type: {media_type}")

    token = await _get_token(bot_hash)
    method, field = _MEDIA_METHOD[media_type]
    contents = await file.read()
    if not contents:
        raise HTTPException(400, "Empty file")

    async with httpx.AsyncClient(timeout=60.0) as client:
        await _validate_chat(client, token, chat_id)

        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption
        if reply_markup:
            data["reply_markup"] = reply_markup  # already JSON-encoded by the caller

        res = await client.post(
            f"{TG}{token}/{method}",
            data=data,
            files={field: (file.filename or media_type, contents, file.content_type)},
        )
        d = res.json()
        if not d.get("ok"):
            raise HTTPException(400, d.get("description", "Send failed"))
        return {"ok": True, "message_id": d["result"]["message_id"]}
