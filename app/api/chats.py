from fastapi import APIRouter, Depends, Query
from app.auth import require_auth
from app.database import db

router = APIRouter(prefix="/api/chats", tags=["chats"])


@router.get("")
async def get_chats(bot_hash: str = Query(...), _=Depends(require_auth)):
    rows = await db.get_chats(bot_hash)
    for r in rows:
        if r.get("last_active"):
            r["last_active"] = r["last_active"].isoformat()
        if r.get("first_seen"):
            r["first_seen"] = r["first_seen"].isoformat()
    return rows
