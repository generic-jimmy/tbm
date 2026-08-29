import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.auth import require_auth
from app.database import db
from app.crypto import decrypt_token
from app.config import get_settings

router = APIRouter(prefix="/api/send", tags=["send"])

TG = "https://api.telegram.org/bot"


class SendRequest(BaseModel):
    bot_hash:   str
    chat_id:    str
    text:       str
    parse_mode: Optional[str] = None


@router.post("")
async def send_message(body: SendRequest, _=Depends(require_auth)):
    bot = await db.get_bot(body.bot_hash)
    if not bot:
        raise HTTPException(404, "Bot not found")

    token = decrypt_token(bot["token_encrypted"], get_settings().secret_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Validate chat
        cr = await client.get(f"{TG}{token}/getChat",
                              params={"chat_id": body.chat_id})
        cd = cr.json()
        if not cd.get("ok"):
            desc = cd.get("description", "Unknown error")
            if "not found" in desc.lower():
                desc += ("\n\n• User must send /start to the bot first\n"
                         "• Groups use negative IDs (e.g. -100123456)")
            raise HTTPException(400, desc)

        payload = {"chat_id": body.chat_id, "text": body.text}
        if body.parse_mode and body.parse_mode != "None":
            payload["parse_mode"] = body.parse_mode

        res = await client.post(f"{TG}{token}/sendMessage", json=payload)
        data = res.json()
        if not data.get("ok"):
            raise HTTPException(400, data.get("description", "Send failed"))
        return {"ok": True, "message_id": data["result"]["message_id"]}
