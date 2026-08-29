import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from app.auth import decode_token
from app.ws import ws_manager

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(...),
    bot_hash: Optional[str] = Query(None),
):
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4001)
        return

    flt = {bot_hash} if bot_hash else None
    await ws_manager.connect(ws, flt)
    try:
        while True:
            await ws.receive_text()   # keep-alive / ignore client messages
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(ws)
