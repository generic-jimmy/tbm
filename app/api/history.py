"""MTProto history import routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.auth import require_auth
from app.database import db

router = APIRouter(prefix="/api/history", tags=["history"])


def _importer():
    from app.main import history_importer
    return history_importer


class ImportRequest(BaseModel):
    bot_hash:     str
    chat_ids:     Optional[list[int]] = None   # None = all known chats
    limit:        Optional[int]        = None   # None = unlimited
    oldest_date:  Optional[datetime]   = None   # None = go back to the start


@router.post("/import")
async def start_import(body: ImportRequest, _=Depends(require_auth)):
    """
    Start a full MTProto history import for one or all chats the bot is in.
    Returns a job_id you can use to track progress via GET /api/history/job/{id}
    or the WebSocket (type: 'import_progress').
    """
    importer = _importer()
    job_id   = await importer.start(
        bot_hash    = body.bot_hash,
        chat_ids    = body.chat_ids,
        limit       = body.limit,
        oldest_date = body.oldest_date,
    )
    return {"job_id": job_id, "status": "started"}


@router.get("/job/{job_id}")
async def get_job(job_id: str, _=Depends(require_auth)):
    """Live progress for a running import job."""
    importer = _importer()
    # Check in-memory first (faster, live)
    live = importer.get_progress(job_id)
    if live:
        return {"job_id": job_id, **live}
    # Fall back to DB (for completed jobs / after restart)
    row = await db.get_import_job(job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    return row


@router.get("/jobs")
async def list_jobs(bot_hash: str = Query(...), _=Depends(require_auth)):
    """Last 20 import jobs for a bot."""
    return await db.get_import_jobs(bot_hash)
