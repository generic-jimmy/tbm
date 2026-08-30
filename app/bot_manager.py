"""Orchestrates all per-bot async worker tasks."""
import asyncio
import logging
from typing import Optional

import httpx

from app.crypto import decrypt_token
from app.config import get_settings
from app.database import Database
from app.ws import ConnectionManager

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self, db: Database, ws: ConnectionManager):
        self._db  = db
        self._ws  = ws
        # bot_hash → {task, worker, username, name, status, error}
        self._registry: dict[str, dict] = {}

    # ── lifecycle ──────────────────────────────────────────────────────────────
    async def start_all(self):
        bots = await self._db.get_active_bots()
        for bot in bots:
            await self.start_bot(bot)
        logger.info(f"BotManager started {len(bots)} worker(s)")

    async def stop_all(self):
        for bot_hash in list(self._registry):
            await self.stop_bot(bot_hash)
        logger.info("BotManager stopped all workers")

    # ── per-bot control ────────────────────────────────────────────────────────
    async def start_bot(self, bot: dict) -> bool:
        from app.bot_worker import BotWorker
        bot_hash = bot["token_hash"]

        entry = self._registry.get(bot_hash)
        if entry and not entry["task"].done():
            return False  # already running

        try:
            token = decrypt_token(bot["token_encrypted"], get_settings().secret_key)
        except Exception as e:
            logger.error(f"Cannot decrypt token for {bot_hash[:8]}: {e}")
            return False

        worker = BotWorker(bot, token, self._db, self._ws, self)
        task   = asyncio.create_task(worker.run(), name=f"bot-{bot_hash[:8]}")
        self._registry[bot_hash] = {
            "task":     task,
            "worker":   worker,
            "username": bot.get("username", ""),
            "name":     bot.get("name", ""),
            "status":   "starting",
            "error":    None,
        }
        logger.info(f"Started worker for @{bot.get('username')} ({bot_hash[:8]})")
        return True

    async def stop_bot(self, bot_hash: str) -> bool:
        entry = self._registry.get(bot_hash)
        if not entry:
            return False
        task = entry["task"]
        if not task.done():
            task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=3.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        self._registry.pop(bot_hash, None)
        await self._db.set_bot_active(bot_hash, False)
        return True

    async def restart_bot(self, bot_hash: str) -> bool:
        bot = await self._db.get_bot(bot_hash)
        if not bot:
            return False
        await self.stop_bot(bot_hash)
        await self._db.set_bot_active(bot_hash, True)
        return await self.start_bot(bot)

    # ── validation helper ──────────────────────────────────────────────────────
    @staticmethod
    async def validate_token(token: str) -> Optional[dict]:
        """Call Telegram getMe; return bot info dict or None if invalid."""
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res  = await client.get(f"https://api.telegram.org/bot{token}/getMe")
                data = res.json()
                if data.get("ok"):
                    return data["result"]
        except Exception:
            pass
        return None

    # ── status ────────────────────────────────────────────────────────────────
    def set_worker_status(self, bot_hash: str, status: str,
                          error: Optional[str] = None):
        if bot_hash in self._registry:
            self._registry[bot_hash]["status"] = status
            self._registry[bot_hash]["error"]  = error

    def get_status(self, bot_hash: str) -> Optional[dict]:
        entry = self._registry.get(bot_hash)
        if not entry:
            return None
        w = entry.get("worker")
        return {
            "bot_hash":     bot_hash,
            "username":     entry.get("username"),
            "name":         entry.get("name"),
            "status":       entry.get("status", "unknown"),
            "error":        entry.get("error"),
            "is_running":   not entry["task"].done(),
            "last_poll_id": w.last_uid if w else 0,
        }

    def get_all_statuses(self) -> list[dict]:
        return [self.get_status(bh) for bh in self._registry]

    def is_running(self, bot_hash: str) -> bool:
        entry = self._registry.get(bot_hash)
        return bool(entry and not entry["task"].done())
