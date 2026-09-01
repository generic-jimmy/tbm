"""Single-bot worker — runs in either polling or webhook mode."""
import asyncio
import logging
import httpx

from app.parser import parse_update
from app.storage import forward_to_storage
from app.database import Database
from app.ws import ConnectionManager
from app.config import get_settings
from app.webhook import webhook_secret_for, webhook_path

logger = logging.getLogger(__name__)

TG = "https://api.telegram.org/bot"

ALLOWED_UPDATES = [
    "message", "edited_message", "channel_post", "edited_channel_post",
]


class BotWorker:
    def __init__(self, bot: dict, token: str, db: Database,
                 ws: ConnectionManager, manager):
        self.bot        = bot
        self.token      = token
        self.bot_hash   = bot["token_hash"]
        self.storage_id = bot.get("storage_chat_id")
        self.db         = db
        self.ws         = ws
        self.manager    = manager
        self.last_uid   = bot.get("last_poll_id", 0)
        self.status     = "starting"
        self.error: str | None = None
        self._settings  = get_settings()
        self.mode       = "webhook" if self._settings.webhook_base_url else "polling"

    async def run(self):
        self._set_status("starting")
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
                if self._settings.history_drain_on_boot:
                    await self._drain_history(client)

                if self.mode == "webhook":
                    await self._start_webhook_mode(client)
                else:
                    await self._start_polling_mode(client)
        except asyncio.CancelledError:
            await self._teardown()
            self._set_status("stopped")
        except Exception as e:
            self._set_status("error", str(e))
            logger.error(f"[{self.bot_hash[:8]}] Worker crashed: {e}")

    # ── webhook mode ─────────────────────────────────────────────────────────
    async def _start_webhook_mode(self, client: httpx.AsyncClient):
        secret = webhook_secret_for(self.bot_hash, self._settings.secret_key)
        url = self._settings.webhook_base_url.rstrip("/") + webhook_path(self.bot_hash)
        res = await client.post(
            f"{TG}{self.token}/setWebhook",
            json={
                "url": url,
                "secret_token": secret,
                "allowed_updates": ALLOWED_UPDATES,
                "max_connections": 40,
                "drop_pending_updates": False,
            },
        )
        data = res.json()
        if not data.get("ok"):
            raise RuntimeError(f"setWebhook failed: {data.get('description')}")

        self._set_status("webhook")
        logger.info(f"[{self.bot_hash[:8]}] Webhook registered → {url}")

        # Updates now arrive via the FastAPI route (app.api.webhook), not this
        # coroutine — just stay alive so BotManager sees the worker as running
        # until it's cancelled (stop/restart/shutdown).
        await asyncio.Event().wait()

    async def handle_webhook_update(self, upd: dict):
        """Entry point called by the /webhook/{bot_hash} route."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            await self._process_update(upd, client, broadcast=True)

    # ── polling mode ─────────────────────────────────────────────────────────
    async def _start_polling_mode(self, client: httpx.AsyncClient):
        self._set_status("polling")
        while True:
            await self._poll_once(client)
            await asyncio.sleep(self._settings.poll_interval_seconds)

    async def _poll_once(self, client: httpx.AsyncClient):
        try:
            res = await client.get(
                f"{TG}{self.token}/getUpdates",
                params={"offset": self.last_uid, "timeout": 5},
                timeout=12.0,
            )
            data = res.json()
        except httpx.TimeoutException:
            return
        except Exception as e:
            logger.warning(f"[{self.bot_hash[:8]}] Poll error: {e}")
            return

        if not data.get("ok"):
            return

        for upd in data["result"]:
            self.last_uid = upd["update_id"] + 1
            await self._process_update(upd, client, broadcast=True)

        if data["result"]:
            await self.db.update_last_poll_id(self.bot_hash, self.last_uid)

    # ── teardown ──────────────────────────────────────────────────────────────
    async def _teardown(self):
        if self.mode == "webhook":
            try:
                async with httpx.AsyncClient(timeout=10.0) as c:
                    await c.post(f"{TG}{self.token}/deleteWebhook")
                logger.info(f"[{self.bot_hash[:8]}] Webhook deregistered")
            except Exception as e:
                logger.warning(f"[{self.bot_hash[:8]}] deleteWebhook failed: {e}")

    # ── history drain (runs once at startup, both modes) ────────────────────
    async def _drain_history(self, client: httpx.AsyncClient):
        self._set_status("draining")
        total = 0
        offset: int | None = None

        logger.info(f"[{self.bot_hash[:8]}] Draining history…")
        while True:
            params = {"limit": 100, "timeout": 0}
            if offset is not None:
                params["offset"] = offset
            try:
                res = await client.get(f"{TG}{self.token}/getUpdates",
                                       params=params, timeout=15.0)
                data = res.json()
            except Exception as e:
                logger.warning(f"[{self.bot_hash[:8]}] Drain request error: {e}")
                break

            if not data.get("ok"):
                logger.warning(f"[{self.bot_hash[:8]}] Drain Telegram error: "
                               f"{data.get('description')}")
                break

            batch = data["result"]
            if not batch:
                break

            for upd in batch:
                uid    = upd["update_id"]
                offset = uid + 1
                self.last_uid = offset
                await self._process_update(upd, client, broadcast=False)
                total += 1

            await self.db.update_last_poll_id(self.bot_hash, self.last_uid)

            if len(batch) < 100:
                break

        logger.info(f"[{self.bot_hash[:8]}] Drain complete — {total} updates")
        await self.ws.broadcast(
            {"type": "bot_status", "bot_hash": self.bot_hash,
             "status": "drain_done", "count": total},
            self.bot_hash,
        )

    # ── process one update (shared by polling, webhook, and drain) ──────────
    async def _process_update(self, upd: dict, client: httpx.AsyncClient,
                              broadcast: bool = True):
        row = parse_update(upd, self.bot_hash)
        if not row:
            return

        if row.get("_chat") and row.get("chat_id"):
            ch = row["_chat"]
            await self.db.upsert_chat(
                ch.get("id"), self.bot_hash,
                ch.get("type", ""), ch.get("title") or ch.get("first_name", ""),
                ch.get("username"),
            )
        if row.get("_sender") and row.get("sender_id"):
            await self.db.upsert_user(row["_sender"], self.bot_hash)

        clean = {k: v for k, v in row.items() if not k.startswith("_")}
        inserted = await self.db.insert_message(clean)

        if not inserted:
            return

        if (self._settings.auto_forward_files
                and self.storage_id
                and row.get("file_id")
                and row.get("chat_id")
                and row.get("msg_id")):
            asyncio.create_task(
                self._forward_file(client, row, clean)
            )

        if broadcast:
            ws_payload = {
                "type":        "new_message",
                "bot_hash":    self.bot_hash,
                "bot_username": self.bot.get("username", ""),
                "id":          None,
                "kind":        clean["kind"],
                "source":      "bot_api",
                "sender_name": clean.get("sender_name"),
                "sender_id":   clean.get("sender_id"),
                "chat_id":     clean.get("chat_id"),
                "chat_title":  clean.get("chat_title"),
                "content":     (clean.get("content") or "")[:200],
                "file_id":     clean.get("file_id"),
                "ts":          clean["ts"].isoformat() if hasattr(clean["ts"], "isoformat")
                               else str(clean["ts"]),
            }
            await self.ws.broadcast(ws_payload, self.bot_hash)
            await self.ws.send_all({"type": "stats_refresh"})

    async def _forward_file(self, client: httpx.AsyncClient,
                            row: dict, clean: dict):
        result = await forward_to_storage(
            client, self.token, self.storage_id,
            row["chat_id"], row["msg_id"],
        )
        if result:
            storage_msg_id, storage_file_id = result
            await self.db.update_tg_storage(
                clean["update_id"], self.bot_hash,
                storage_msg_id, storage_file_id or "",
            )

    def _set_status(self, status: str, error: str = None):
        self.status = status
        self.error  = error
        self.manager.set_worker_status(self.bot_hash, status, error)
