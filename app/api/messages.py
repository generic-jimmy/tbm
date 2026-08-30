from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.auth import require_auth
from app.database import db

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
async def get_messages(
    bot_hash:  str,
    kind:      Optional[str] = Query(None),
    chat_id:   Optional[int] = Query(None),
    search:    Optional[str] = Query(None),
    source:    Optional[str] = Query(None),   # 'bot_api' | 'telethon' | None=all
    limit:     int            = Query(100, ge=1, le=500),
    before_ts: Optional[str] = Query(None),
    _=Depends(require_auth),
):
    return await db.get_messages(
        bot_hash, kind, chat_id, search, source, limit, before_ts
    )
