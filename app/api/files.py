import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.auth import require_auth
from app.database import db
from app.crypto import decrypt_token
from app.config import get_settings

router = APIRouter(prefix="/api/files", tags=["files"])

TG     = "https://api.telegram.org/bot"
TG_CDN = "https://api.telegram.org/file/bot"


async def _get_token(bot_hash: str) -> str:
    bot = await db.get_bot(bot_hash)
    if not bot:
        raise HTTPException(404, "Bot not found")
    return decrypt_token(bot["token_encrypted"], get_settings().secret_key)


@router.get("/{file_id}/info")
async def file_info(file_id: str, bot_hash: str,
                    _=Depends(require_auth)):
    token = await _get_token(bot_hash)
    async with httpx.AsyncClient(timeout=10.0) as client:
        res  = await client.get(f"{TG}{token}/getFile",
                                params={"file_id": file_id})
        data = res.json()
        if not data.get("ok"):
            raise HTTPException(400, data.get("description"))
        return data["result"]


@router.get("/{file_id}/download")
async def download_file(file_id: str, bot_hash: str,
                        _=Depends(require_auth)):
    token = await _get_token(bot_hash)
    async with httpx.AsyncClient(timeout=10.0) as client:
        info = await client.get(f"{TG}{token}/getFile",
                                params={"file_id": file_id})
        d = info.json()
        if not d.get("ok"):
            raise HTTPException(400, d.get("description"))
        file_path = d["result"]["file_path"]
        fname = file_path.split("/")[-1]

    # Stream file back to browser
    async def _stream():
        async with httpx.AsyncClient(timeout=120.0) as c:
            async with c.stream("GET", f"{TG_CDN}{token}/{file_path}") as r:
                async for chunk in r.aiter_bytes(8192):
                    yield chunk

    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
