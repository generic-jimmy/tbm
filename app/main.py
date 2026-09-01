"""FastAPI application — entry point."""
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import db
from app.ws import ws_manager
from app.bot_manager import BotManager
from app.telethon_importer import HistoryImporter

# ── Routers ───────────────────────────────────────────────────────────────────
from app.api.auth      import router as auth_router
from app.api.bots      import router as bots_router
from app.api.messages  import router as messages_router
from app.api.stats     import router as stats_router
from app.api.send      import router as send_router
from app.api.files     import router as files_router
from app.api.chats     import router as chats_router
from app.api.export    import router as export_router
from app.api.ws_route  import router as ws_router
from app.api.history   import router as history_router
from app.api.webhook   import router as webhook_router
from app.api.templates import router as templates_router

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Module-level singletons (referenced by api sub-modules) ───────────────────
bot_manager      = BotManager(db, ws_manager)
history_importer = HistoryImporter(db, ws_manager)

_resync_task: asyncio.Task | None = None


async def _scheduled_resync_loop():
    """Periodically re-sync every known chat for every MTProto-enabled bot.

    Incremental only (min_id watermark from import_checkpoints) — cheap,
    and safe to run indefinitely alongside live polling/webhook delivery.
    """
    s = get_settings()
    interval = s.resync_interval_hours * 3600
    logger.info(f"Scheduled MTProto re-sync enabled — every {s.resync_interval_hours}h")
    while True:
        await asyncio.sleep(interval)
        try:
            bots = await db.get_active_bots()
            for bot in bots:
                chats = await db.get_chats(bot["token_hash"])
                if not chats:
                    continue
                logger.info(
                    f"[resync] {bot.get('username')}: "
                    f"syncing {len(chats)} known chat(s)"
                )
                await history_importer.start(
                    bot_hash=bot["token_hash"],
                    chat_ids=None,
                    incremental=True,
                )
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[resync] loop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _resync_task
    s = get_settings()
    await db.connect(s.database_url)
    logger.info("Database connected")

    if not s.telegram_api_id or not s.telegram_api_hash:
        logger.warning(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH not set — "
            "MTProto history import disabled. "
            "Get them free from https://my.telegram.org"
        )

    if s.webhook_base_url:
        logger.info(f"Webhook mode enabled — base URL {s.webhook_base_url}")
    else:
        logger.info("Polling mode (set WEBHOOK_BASE_URL to switch to webhooks)")

    await bot_manager.start_all()

    if s.resync_interval_hours and s.resync_interval_hours > 0:
        _resync_task = asyncio.create_task(_scheduled_resync_loop())

    yield

    if _resync_task:
        _resync_task.cancel()
        try:
            await _resync_task
        except asyncio.CancelledError:
            pass

    await bot_manager.stop_all()
    await db.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Telegram Bot Manager API",
    version="2.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── No CORS middleware: frontend and backend are always same-origin ────────────
# In dev, Vite proxies /api → localhost:8000.
# In production, everything is served from a single container on one port.
# Adding CORS with allow_origins=["*"] + allow_credentials=True is both
# unnecessary and technically invalid per the CORS spec.

for r in [
    auth_router, bots_router, messages_router, stats_router,
    send_router, files_router, chats_router, export_router,
    history_router, ws_router, webhook_router, templates_router,
]:
    app.include_router(r)


@app.get("/health")
async def health():
    s = get_settings()
    return {
        "status":        "ok",
        "bots":          len(bot_manager.get_all_statuses()),
        "mtproto_ready": bool(s.telegram_api_id and s.telegram_api_hash),
        "mode":          "webhook" if s.webhook_base_url else "polling",
    }


# ── Serve React SPA — registered LAST so API routes take priority ─────────────
_static = Path(__file__).parent / "static"
_assets = _static / "assets"

if _static.exists():
    if _assets.exists():
        # Serve Vite-compiled bundles at /assets/index-xxx.{js,css}
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    _index = str(_static / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        """Return index.html for every unmatched *client-route* GET request.

        This is what makes React Router work correctly on page refresh and
        deep-links like /monitor, /compose, /bots — Starlette's built-in
        StaticFiles(html=True) does NOT do this; it only serves index.html
        for the exact root path and 404s on anything else.

        Paths that look like API/WS/asset/webhook routes but didn't match
        any registered route (typos, wrong method) still get a real 404
        instead of silently returning the HTML shell.
        """
        if full_path.startswith(("api/", "ws", "assets/", "health", "webhook")):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        return FileResponse(_index)
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return JSONResponse({
            "message": "TBM API v2.2 running — frontend not built yet.",
            "hint":    "cd frontend && npm install && npm run build",
            "docs":    "/api/docs",
        })

