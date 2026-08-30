"""WebSocket connection manager — fan-out to browser clients."""
import asyncio
import logging
from typing import Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # ws -> set of bot_hashes to listen to (None = all)
        self._conns: dict[WebSocket, Optional[set[str]]] = {}

    async def connect(self, ws: WebSocket, bot_hashes: Optional[set[str]] = None):
        await ws.accept()
        self._conns[ws] = bot_hashes
        logger.debug(f"WS connected; total={len(self._conns)}")

    def disconnect(self, ws: WebSocket):
        self._conns.pop(ws, None)
        logger.debug(f"WS disconnected; total={len(self._conns)}")

    async def broadcast(self, payload: dict, bot_hash: str):
        dead: list[WebSocket] = []
        for ws, flt in list(self._conns.items()):
            if flt is not None and bot_hash not in flt:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    async def send_all(self, payload: dict):
        """Broadcast to every connected client regardless of bot filter."""
        dead: list[WebSocket] = []
        for ws in list(self._conns):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def client_count(self) -> int:
        return len(self._conns)


ws_manager = ConnectionManager()
