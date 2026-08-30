"""FastAPI application — entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import db
from app.ws import ws_manager
from app.bot_manager import BotManager
from app.telethon_importer import HistoryImporter

# Routers
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

logging.basicConfig(
    level=getattr(logging, get_settings().log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Module-level singletons (imported by api sub-modules)
bot_manager      = BotManager(db, ws_manager)
history_importer = HistoryImporter(db, ws_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    await db.connect(s.database_url)
    logger.info("Database connected")

    if not s.telegram_api_id or not s.telegram_api_hash:
        logger.warning(
            "TELEGRAM_API_ID / TELEGRAM_API_HASH not set — "
            "MTProto history import will not work. "
            "Get them free from https://my.telegram.org"
        )

    await bot_manager.start_all()
    yield
    await bot_manager.stop_all()
    await db.disconnect()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Telegram Bot Manager API",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [
    auth_router, bots_router, messages_router, stats_router,
    send_router,  files_router, chats_router,  export_router,
    history_router, ws_router,
]:
    app.include_router(r)


@app.get("/health")
async def health():
    s   = get_settings()
    mtproto_ready = bool(s.telegram_api_id and s.telegram_api_hash)
    return {
        "status":        "ok",
        "bots":          len(bot_manager.get_all_statuses()),
        "mtproto_ready": mtproto_ready,
    }


# ==============================================================================
# SPA MOUNT & ROUTING INTERCEPTOR
# ==============================================================================
_static = Path(__file__).parent / "static"

if _static.exists():
    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback_handler(request: Request, exc: StarletteHTTPException):
        # Intercept 404s for frontend routes and serve index.html.
        # Bypass SPA fallback for backend API routes (assuming /api prefix) or docs.
        if exc.status_code == 404 and not request.url.path.startswith(("/api", "/docs")):
            index_path = _static / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path))
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.mount("/", StaticFiles(directory=str(_static), html=True), name="spa")
else:
    @app.get("/")
    async def root():
        return JSONResponse({
            "message": "TBM API v2.1 running. Frontend not built yet.",
            "docs": "/api/docs",
        })
