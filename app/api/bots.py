from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.auth import require_auth
from app.database import db
from app.crypto import encrypt_token, hash_token
from app.bot_manager import BotManager

router = APIRouter(prefix="/api/bots", tags=["bots"])


def _get_manager() -> BotManager:
    from app.main import bot_manager
    return bot_manager


class AddBotRequest(BaseModel):
    token: str
    storage_chat_id: Optional[int] = None


class UpdateStorageRequest(BaseModel):
    storage_chat_id: int


@router.get("")
async def list_bots(_=Depends(require_auth)):
    bots = await db.get_all_bots()
    manager = _get_manager()
    result = []
    for b in bots:
        status = manager.get_status(b["token_hash"]) or {}
        result.append({
            "token_hash":     b["token_hash"],
            "username":       b["username"],
            "name":           b["name"],
            "bot_id":         b["bot_id"],
            "storage_chat_id":b["storage_chat_id"],
            "is_active":      b["is_active"],
            "last_poll_id":   b["last_poll_id"],
            "created_at":     b["created_at"].isoformat() if b.get("created_at") else None,
            "worker_status":  status.get("status", "stopped"),
            "worker_error":   status.get("error"),
            "is_running":     status.get("is_running", False),
        })
    return result


@router.post("")
async def add_bot(body: AddBotRequest, _=Depends(require_auth)):
    manager = _get_manager()
    from app.config import get_settings

    info = await BotManager.validate_token(body.token)
    if not info:
        raise HTTPException(status_code=400, detail="Invalid bot token")

    token_hash = hash_token(body.token)
    encrypted  = encrypt_token(body.token, get_settings().secret_key)

    bot_row = await db.upsert_bot({
        "token_hash":      token_hash,
        "token_encrypted": encrypted,
        "username":        info.get("username"),
        "name":            info.get("first_name"),
        "bot_id":          info.get("id"),
        "storage_chat_id": body.storage_chat_id,
    })

    started = await manager.start_bot(bot_row)
    return {
        "token_hash": token_hash,
        "username":   info.get("username"),
        "name":       info.get("first_name"),
        "started":    started,
    }


@router.delete("/{token_hash}")
async def remove_bot(token_hash: str, _=Depends(require_auth)):
    await _get_manager().stop_bot(token_hash)
    await db.delete_bot(token_hash)
    return {"deleted": True}


@router.post("/{token_hash}/start")
async def start_bot(token_hash: str, _=Depends(require_auth)):
    bot = await db.get_bot(token_hash)
    if not bot:
        raise HTTPException(404, "Bot not found")
    await db.set_bot_active(token_hash, True)
    started = await _get_manager().start_bot(bot)
    return {"started": started}


@router.post("/{token_hash}/stop")
async def stop_bot(token_hash: str, _=Depends(require_auth)):
    stopped = await _get_manager().stop_bot(token_hash)
    return {"stopped": stopped}


@router.post("/{token_hash}/restart")
async def restart_bot(token_hash: str, _=Depends(require_auth)):
    ok = await _get_manager().restart_bot(token_hash)
    return {"restarted": ok}


@router.put("/{token_hash}/storage")
async def update_storage(token_hash: str, body: UpdateStorageRequest,
                         _=Depends(require_auth)):
    await db.update_bot_storage(token_hash, body.storage_chat_id)
    return {"updated": True}


@router.get("/{token_hash}/status")
async def bot_status(token_hash: str, _=Depends(require_auth)):
    status = _get_manager().get_status(token_hash)
    if not status:
        raise HTTPException(404, "Bot not found or not running")
    return status
