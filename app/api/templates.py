"""Saved reply templates for Compose."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.auth import require_auth
from app.database import db

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateIn(BaseModel):
    name: str
    text: str
    reply_markup: Optional[dict] = None   # {"inline_keyboard": [[{"text":..,"url":..}]]}


@router.get("")
async def list_templates(_=Depends(require_auth)):
    return await db.get_templates()


@router.post("")
async def create_template(body: TemplateIn, _=Depends(require_auth)):
    if not body.name.strip() or not body.text.strip():
        raise HTTPException(400, "Name and text are required")
    return await db.create_template(body.name.strip(), body.text, body.reply_markup)


@router.delete("/{template_id}")
async def delete_template(template_id: int, _=Depends(require_auth)):
    await db.delete_template(template_id)
    return {"deleted": True}
