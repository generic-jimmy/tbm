"""
MTProto history importer using Telethon with a bot token.
No phone number or user account needed — api_id + api_hash + bot_token only.

What this can access:
  ✔ Full message history of any group/channel the bot is a member of
  ✔ Goes back to the very first message (not just 24h like Bot API)
  ✔ All message types: text, media, documents, polls, etc.
  ✗ DMs between other users
  ✗ History from before the bot joined the chat (Telegram server enforces this)

Resumability & incremental sync
--------------------------------
Every chat gets a checkpoint row in `import_checkpoints`:
  - earliest_id: the oldest msg_id imported so far. A full-history import
    always resumes from here automatically (via `offset_id`) instead of
    restarting from scratch after a crash or a stopped job.
  - latest_id: the newest msg_id imported so far. Incremental re-syncs
    (manual "Sync new messages" or the scheduled background job) use this
    as a `min_id` watermark to fetch only what's new.

Media download (optional)
--------------------------
Telethon's internal file references are not valid Bot API file_ids, so
imported media isn't downloadable through /api/files/.../download the way
live-polled media is. When `download_media=True` and the bot has a storage
group configured, each media message is pulled via MTProto and immediately
re-uploaded through the Bot API to the storage group — after which it has
a real file_id and behaves identically to live-forwarded media. This is
opt-in because it multiplies bandwidth/time per message.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import types as tl
from telethon.errors import (
    ChatAdminRequiredError, ChannelPrivateError,
    FloodWaitError, RPCError,
)

from app.config import get_settings
from app.crypto import decrypt_token
from app.database import Database
from app.storage import upload_media_to_storage
from app.ws import ConnectionManager

logger = logging.getLogger(__name__)

DOWNLOADABLE_KINDS = {"photo", "document", "video", "audio", "voice"}


# ─────────────────────────────────────────────────────────────────────────────
#  Parse a Telethon Message into our DB row format
# ─────────────────────────────────────────────────────────────────────────────
def _parse_telethon_msg(msg, bot_hash: str,
                         chat_id: int, chat_title: str,
                         sender_cache: dict) -> Optional[dict]:
    if not isinstance(msg, tl.Message) or msg.date is None:
        return None

    # ── sender ────────────────────────────────────────────────────────────────
    sender_id   = msg.sender_id
    sender_name = sender_cache.get(sender_id, f"user:{sender_id}")

    # ── media type ────────────────────────────────────────────────────────────
    kind  = "text"
    fid   = None
    fname = None
    fsize = None
    mime  = None
    body  = msg.text or msg.message or ""
    w = h = dur = lat = lon = None
    cap   = None

    if msg.media:
        media = msg.media

        if isinstance(media, tl.MessageMediaPhoto):
            kind = "photo"
            if hasattr(media, "photo") and media.photo:
                if hasattr(media.photo, "sizes") and media.photo.sizes:
                    biggest = max(
                        (s for s in media.photo.sizes
                         if hasattr(s, "w") and hasattr(s, "h")),
                        key=lambda s: getattr(s, "w", 0),
                        default=None,
                    )
                    if biggest:
                        w, h = getattr(biggest, "w", None), getattr(biggest, "h", None)
            body = f"Photo {w or '?'}×{h or '?'}"
            cap  = msg.text or None

        elif isinstance(media, tl.MessageMediaDocument):
            doc   = media.document
            mime  = getattr(doc, "mime_type", None)
            fsize = getattr(doc, "size",      None)

            for attr in getattr(doc, "attributes", []):
                if isinstance(attr, tl.DocumentAttributeVideo):
                    kind = "video"
                    dur  = attr.duration
                    w, h = attr.w, attr.h
                    break
                elif isinstance(attr, tl.DocumentAttributeAudio):
                    kind = "voice" if attr.voice else "audio"
                    dur  = attr.duration
                    fname = getattr(attr, "title", None)
                    break
                elif isinstance(attr, tl.DocumentAttributeSticker):
                    kind = "sticker"
                    body = f"Sticker {getattr(attr, 'alt', '')}"
                    break
                elif isinstance(attr, tl.DocumentAttributeFilename):
                    fname = attr.file_name

            if kind == "text":
                kind = "document"
            if kind == "document" and not body:
                body = f"File: {fname or 'unknown'}  ({fsize or '?'} bytes)"
            elif kind == "video":
                body = f"Video {dur}s  {w}×{h}"
            elif kind in ("audio", "voice"):
                body = f"{'Voice' if kind == 'voice' else 'Audio'} {dur}s"
            cap = msg.text or None

        elif isinstance(media, tl.MessageMediaGeo):
            kind = "location"
            geo  = media.geo
            if isinstance(geo, tl.GeoPoint):
                lat, lon = geo.lat, geo.long
                body = f"Location: {lat}, {lon}"

        elif isinstance(media, tl.MessageMediaGeoLive):
            kind = "location"
            geo  = media.geo
            if isinstance(geo, tl.GeoPoint):
                lat, lon = geo.lat, geo.long
                body = f"Live Location: {lat}, {lon}"

        elif isinstance(media, tl.MessageMediaContact):
            kind = "contact"
            body = (f"{media.first_name} {media.last_name}\n"
                    f"{media.phone_number}").strip()

        elif isinstance(media, tl.MessageMediaPoll):
            kind = "text"
            body = f"Poll: {media.poll.question}"

        elif isinstance(media, tl.MessageMediaWebPage):
            kind = "text"

    if cap:
        body = (body + f"\n📝 {cap}").strip() if body else cap

    # ── forward ───────────────────────────────────────────────────────────────
    fwd_from = None
    is_fwd   = False
    if msg.forward:
        is_fwd = True
        fwd    = msg.forward
        fwd_id = getattr(fwd, "sender_id", None) or getattr(fwd, "channel_id", None)
        fwd_from = (sender_cache.get(fwd_id, "")
                    or str(fwd_id) if fwd_id else "")

    # ── reply ─────────────────────────────────────────────────────────────────
    reply_to = None
    if msg.reply_to and hasattr(msg.reply_to, "reply_to_msg_id"):
        reply_to = msg.reply_to.reply_to_msg_id

    ts = msg.date
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    return {
        "msg_id":       msg.id,
        "bot_hash":     bot_hash,
        "kind":         kind,
        "sender_id":    sender_id,
        "sender_name":  sender_name,
        "chat_id":      chat_id,
        "chat_title":   chat_title,
        "content":      body or "",
        "caption":      cap,
        "file_id":      fid,       # Telethon file refs ≠ Bot API file_ids
        "file_name":    fname,
        "file_size":    fsize,
        "mime_type":    mime,
        "is_forwarded": is_fwd,
        "fwd_from":     fwd_from,
        "reply_to_id":  reply_to,
        "is_edited":    bool(getattr(msg, "edit_date", None)),
        "is_deleted":   False,
        "width":  w,  "height": h, "duration": dur,
        "latitude": lat, "longitude": lon,
        "ts":       ts,
    }


# ─────────────────────────────────────────────────────────────────────────────
#  Importer
# ─────────────────────────────────────────────────────────────────────────────
class HistoryImporter:
    def __init__(self, db: Database, ws: ConnectionManager):
        self._db  = db
        self._ws  = ws
        # job_id → live progress dict (in-memory for fast WS updates)
        self._live: dict[str, dict] = {}

    async def start(
        self,
        bot_hash:       str,
        chat_ids:       list[int] | None = None,
        limit:          int | None       = None,
        oldest_date:    datetime | None  = None,
        incremental:    bool             = False,
        download_media: bool             = False,
    ) -> str:
        job_id = uuid.uuid4().hex[:10]
        self._live[job_id] = {
            "status":       "pending",
            "imported":     0,
            "skipped":      0,
            "errors":       0,
            "current_chat": None,
            "incremental":  incremental,
        }
        db_chat_id = chat_ids[0] if chat_ids and len(chat_ids) == 1 else None
        await self._db.create_import_job(job_id, bot_hash, db_chat_id)
        asyncio.create_task(
            self._run(job_id, bot_hash, chat_ids, limit, oldest_date,
                      incremental, download_media),
            name=f"import-{job_id}",
        )
        return job_id

    def get_progress(self, job_id: str) -> Optional[dict]:
        return self._live.get(job_id)

    # ── runner ────────────────────────────────────────────────────────────────
    async def _run(
        self,
        job_id:         str,
        bot_hash:       str,
        chat_ids:       list[int] | None,
        limit:          int | None,
        oldest_date:    datetime | None,
        incremental:    bool,
        download_media: bool,
    ):
        s   = get_settings()
        bot = await self._db.get_bot(bot_hash)
        if not bot:
            await self._fail(job_id, bot_hash, "Bot not found in DB")
            return

        if not s.telegram_api_id or not s.telegram_api_hash:
            await self._fail(job_id, bot_hash,
                "TELEGRAM_API_ID / TELEGRAM_API_HASH not set in env. "
                "Get them free from my.telegram.org")
            return

        try:
            token = decrypt_token(bot["token_encrypted"], s.secret_key)
        except Exception as e:
            await self._fail(job_id, bot_hash, f"Token decrypt failed: {e}")
            return

        session_str = bot.get("telethon_session") or ""
        client      = TelegramClient(
            StringSession(session_str),
            s.telegram_api_id,
            s.telegram_api_hash,
        )

        storage_id  = bot.get("storage_chat_id") if download_media else None
        http_client: Optional[httpx.AsyncClient] = None
        if storage_id:
            http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))

        try:
            await client.start(bot_token=token)

            new_session = client.session.save()
            if new_session != session_str:
                await self._db.update_telethon_session(bot_hash, new_session)

            await self._update(job_id, bot_hash, status="running")

            if chat_ids:
                targets = chat_ids
            else:
                known   = await self._db.get_chats(bot_hash)
                targets = [c["chat_id"] for c in known]

            if not targets:
                await self._fail(job_id, bot_hash,
                    "No chats found. Add a chat_id or let the bot receive a "
                    "message first so chats are auto-discovered.")
                return

            total_imported = 0
            total_skipped  = 0

            for chat_id in targets:
                imp, skip = await self._import_chat(
                    client, http_client, token, storage_id,
                    job_id, bot_hash, chat_id, limit, oldest_date,
                    incremental,
                )
                total_imported += imp
                total_skipped  += skip

            await self._update(job_id, bot_hash,
                status="done",
                imported=total_imported,
                skipped=total_skipped,
                finished_at=datetime.now(timezone.utc),
            )
            logger.info(
                f"[import-{job_id}] Done — "
                f"{total_imported} imported, {total_skipped} skipped"
            )

        except Exception as e:
            logger.error(f"[import-{job_id}] Crashed: {e}")
            await self._fail(job_id, bot_hash, str(e))
        finally:
            await client.disconnect()
            if http_client:
                await http_client.aclose()

    async def _import_chat(
        self,
        client:      TelegramClient,
        http_client: Optional[httpx.AsyncClient],
        token:       str,
        storage_id:  Optional[int],
        job_id:      str,
        bot_hash:    str,
        chat_id:     int,
        limit:       int | None,
        oldest_date: datetime | None,
        incremental: bool,
    ) -> tuple[int, int]:
        try:
            entity = await client.get_entity(chat_id)
        except (ValueError, ChannelPrivateError, ChatAdminRequiredError) as e:
            logger.warning(f"[import-{job_id}] Cannot access chat {chat_id}: {e}")
            return 0, 0

        chat_title = (
            getattr(entity, "title",      None)
            or getattr(entity, "first_name", None)
            or str(chat_id)
        )

        await self._update(job_id, bot_hash,
            current_chat=f"{chat_title} ({chat_id})")
        logger.info(
            f"[import-{job_id}] {'Syncing' if incremental else 'Importing'} "
            f"'{chat_title}' ({chat_id})"
        )

        sender_cache: dict[int, str] = {}
        try:
            async for p in client.iter_participants(entity, limit=500):
                name = (
                    f"{getattr(p,'first_name','') or ''} "
                    f"{getattr(p,'last_name','') or ''}".strip()
                    or getattr(p, "username", None)
                    or str(p.id)
                )
                sender_cache[p.id] = name
        except Exception:
            pass  # Some chat types don't allow iter_participants

        # ── resolve resume point ─────────────────────────────────────────────
        checkpoint = await self._db.get_checkpoint(bot_hash, chat_id)
        earliest_seen = (checkpoint or {}).get("earliest_id")
        latest_seen   = (checkpoint or {}).get("latest_id") or 0

        iter_kwargs = dict(limit=limit, offset_date=oldest_date)
        if incremental:
            # Only fetch what's newer than the last message we've seen —
            # oldest-first within that range so latest_seen advances cleanly.
            iter_kwargs["min_id"]  = latest_seen
            iter_kwargs["reverse"] = True
        elif earliest_seen:
            # Continue a previously interrupted/stopped full-history crawl
            # instead of re-walking from the newest message every time.
            iter_kwargs["offset_id"] = earliest_seen
            logger.info(
                f"[import-{job_id}] Resuming '{chat_title}' from "
                f"msg_id {earliest_seen}"
            )

        imported = 0
        skipped  = 0

        try:
            async for msg in client.iter_messages(entity, **iter_kwargs):
                row = _parse_telethon_msg(
                    msg, bot_hash, chat_id, chat_title, sender_cache
                )
                if not row:
                    skipped += 1
                    continue

                exists = await self._db.message_exists(msg.id, chat_id, bot_hash)
                if exists:
                    skipped += 1
                else:
                    if (http_client and storage_id
                            and row["kind"] in DOWNLOADABLE_KINDS and msg.media):
                        stored = await self._download_and_store(
                            client, http_client, token, storage_id, msg, row,
                        )
                        if stored:
                            row["tg_storage_msg_id"], row["tg_storage_file_id"] = stored

                    ok = await self._db.insert_telethon_message(row)
                    if ok:
                        imported += 1
                    else:
                        skipped += 1

                if earliest_seen is None or msg.id < earliest_seen:
                    earliest_seen = msg.id
                if msg.id > latest_seen:
                    latest_seen = msg.id

                if (imported + skipped) % 100 == 0:
                    await self._db.set_checkpoint(
                        bot_hash, chat_id,
                        earliest_id=earliest_seen, latest_id=latest_seen,
                    )
                    await self._update(job_id, bot_hash,
                        imported=self._live[job_id]["imported"] + imported,
                        skipped=self._live[job_id]["skipped"]  + skipped,
                        current_chat=f"{chat_title} ({chat_id})",
                    )

                if (imported + skipped) % 500 == 0:
                    await asyncio.sleep(0.5)   # respect Telegram's rate limits

        except FloodWaitError as e:
            logger.warning(
                f"[import-{job_id}] FloodWait {e.seconds}s for chat {chat_id}")
            await asyncio.sleep(e.seconds)
        except RPCError as e:
            logger.warning(f"[import-{job_id}] RPC error in chat {chat_id}: {e}")

        # Always persist the checkpoint reached so far, even on partial failure —
        # this is what makes the next run resumable instead of starting over.
        await self._db.set_checkpoint(
            bot_hash, chat_id, earliest_id=earliest_seen, latest_id=latest_seen,
        )

        return imported, skipped

    async def _download_and_store(
        self, client: TelegramClient, http_client: httpx.AsyncClient,
        token: str, storage_id: int, msg, row: dict,
    ) -> Optional[tuple[int, str]]:
        try:
            data = await client.download_media(msg, file=bytes)
        except Exception as e:
            logger.warning(f"Media download failed for msg {msg.id}: {e}")
            return None
        if not data:
            return None
        filename = row.get("file_name") or f"{row['kind']}_{msg.id}"
        return await upload_media_to_storage(
            http_client, token, storage_id, data, filename, row["kind"],
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    async def _update(self, job_id: str, bot_hash: str, **kwargs):
        if job_id in self._live:
            self._live[job_id].update(kwargs)

        db_kwargs = {k: v for k, v in kwargs.items()
                     if k in ("status","imported","skipped","current_chat",
                               "error","finished_at")}
        if db_kwargs:
            # asyncpg requires a real datetime object for TIMESTAMPTZ columns —
            # passing an ISO string here raises DataError. Keep finished_at as
            # a datetime all the way to this call.
            await self._db.update_import_job(job_id, **db_kwargs)

        # WebSocket.send_json() uses the stdlib json module with no datetime
        # support (unlike FastAPI's HTTP responses, which auto-encode via
        # jsonable_encoder) — stringify any datetime values just for this
        # broadcast payload, not the DB write above.
        def _jsonable(v):
            return v.isoformat() if isinstance(v, datetime) else v

        snapshot = {k: _jsonable(v) for k, v in self._live.get(job_id, {}).items()}
        update   = {k: _jsonable(v) for k, v in kwargs.items()}
        await self._ws.broadcast(
            {"type": "import_progress", "job_id": job_id, **snapshot, **update},
            bot_hash,
        )

    async def _fail(self, job_id: str, bot_hash: str, error: str):
        await self._update(job_id, bot_hash, status="error", error=error,
                           finished_at=datetime.now(timezone.utc))
        logger.error(f"[import-{job_id}] {error}")
