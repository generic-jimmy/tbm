from fastapi import APIRouter, Depends, Query
from typing import Optional
from app.auth import require_auth
from app.database import db

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def global_stats(_=Depends(require_auth)):
    return await db.get_all_stats()


@router.get("/bot")
async def bot_stats(bot_hash: str = Query(...), _=Depends(require_auth)):
    return await db.get_message_stats(bot_hash)
