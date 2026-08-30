import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Adjust these imports if your internal module names differ
from app.database import db
# from app.bot_manager import bot_manager  # Uncomment if bot_manager is imported here
# from app.api import router as api_router # Uncomment if you have an API router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if DATABASE_URL:
        await db.connect(DATABASE_URL)
        logger.info("Database connected")
    
    # If your bot manager is initialized here, start it:
    # await bot_manager.start()
    
    yield
    
    # Shutdown
    # await bot_manager.stop()
    await db.disconnect()

app = FastAPI(lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include your API routes here (must come BEFORE the React SPA logic)
# app.include_router(api_router, prefix="/api")


# ── Serve React SPA — must be LAST ───────────────────────────────────────────
_static_base = Path(__file__).parent / "static"
_index = None
_spa_dir = None

# Hunt for index.html anywhere inside the static directory
if _static_base.exists():
    if (_static_base / "index.html").exists():
        _index = _static_base / "index.html"
        _spa_dir = _static_base
    else:
        # Check if a bundler nested it (e.g., static/dist/index.html)
        for path in _static_base.rglob("index.html"):
            _index = path
            _spa_dir = path.parent
            break

if _spa_dir and _index:
    
    @app.exception_handler(404)
    async def spa_fallback_handler(request: Request, exc):
        # If an API route throws a 404, return standard JSON
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        
        # Otherwise, let React Router handle the route
        return FileResponse(_index)

    # Mount the specific directory where index.html was actually found
    app.mount("/", StaticFiles(directory=str(_spa_dir), html=True), name="spa")

else:
    # If index.html is entirely missing, print out what files actually exist
    @app.get("/")
    async def root():
        try:
            # Build a list of every file in the static directory to debug
            files = [str(p.relative_to(_static_base)) for p in _static_base.rglob("*")]
        except Exception:
            files = ["static_dir_missing_entirely"]

        return JSONResponse({
            "message": "TBM API v2.1 running. Frontend not built yet.",
            "docs": "/api/docs",
            "debug_files_found_in_docker": files
        })
