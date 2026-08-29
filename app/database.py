"""asyncpg connection pool + all DB helper methods."""
import asyncpg
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

SCHEMA = """
-- ── core tables ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bots (
    id               BIGSERIAL PRIMARY KEY,
    token_hash       TEXT UNIQUE NOT NULL,
    token_encrypted  TEXT NOT NULL,
    username         TEXT,
    name             TEXT,
    bot_id           BIGINT,
    storage_chat_id  BIGINT,
    is_active        BOOLEAN DEFAULT TRUE,
    last_poll_id     BIGINT DEFAULT 0,
    telethon_session TEXT,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chats (
    id          BIGSERIAL PRIMARY KEY,
    chat_id     BIGINT NOT NULL,
    bot_hash    TEXT NOT NULL,
    type        TEXT,
    title       TEXT,
    username    TEXT,
    first_seen  TIMESTAMPTZ DEFAULT NOW(),
    last_active TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(chat_id, bot_hash)
);

CREATE TABLE IF NOT EXISTS users (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL,
    bot_hash   TEXT NOT NULL,
    first_name TEXT,
    last_name  TEXT,
    username   TEXT,
    is_bot     BOOLEAN DEFAULT FALSE,
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, bot_hash)
);

CREATE TABLE IF NOT EXISTS messages (
    id                  BIGSERIAL PRIMARY KEY,
    msg_id              BIGINT,
    bot_hash            TEXT NOT NULL,
    update_id           BIGINT,             -- NULL for MTProto-imported messages
    kind                TEXT NOT NULL,
    sender_id           BIGINT,
    sender_name         TEXT,
    chat_id             BIGINT,
    chat_title          TEXT,
    content             TEXT,
    caption             TEXT,
    file_id             TEXT,
    file_name           TEXT,
    file_size           BIGINT,
    mime_type           TEXT,
    tg_storage_msg_id   BIGINT,
    tg_storage_file_id  TEXT,
    is_forwarded        BOOLEAN DEFAULT FALSE,
    fwd_from            TEXT,
    reply_to_id         BIGINT,
    is_edited           BOOLEAN DEFAULT FALSE,
    is_deleted          BOOLEAN DEFAULT FALSE,
    width               INTEGER,
    height              INTEGER,
    duration            INTEGER,
    latitude            DOUBLE PRECISION,
    longitude           DOUBLE PRECISION,
    raw_json            JSONB,
    source              TEXT DEFAULT 'bot_api',  -- 'bot_api' | 'telethon'
    ts                  TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- Bot API messages: unique on update_id
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_botapi_dedup
    ON messages(update_id, bot_hash)
    WHERE update_id IS NOT NULL;

-- MTProto messages: unique on msg_id + chat_id + bot_hash
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_telethon_dedup
    ON messages(msg_id, chat_id, bot_hash)
    WHERE source = 'telethon';

-- General indexes
CREATE INDEX IF NOT EXISTS idx_msg_bot_hash  ON messages(bot_hash);
CREATE INDEX IF NOT EXISTS idx_msg_chat_id   ON messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_msg_kind      ON messages(kind);
CREATE INDEX IF NOT EXISTS idx_msg_ts        ON messages(ts DESC);
CREATE INDEX IF NOT EXISTS idx_msg_file_id   ON messages(file_id) WHERE file_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_msg_sender_id ON messages(sender_id);
CREATE INDEX IF NOT EXISTS idx_msg_source    ON messages(source);
CREATE INDEX IF NOT EXISTS idx_chat_bot      ON chats(bot_hash);
CREATE INDEX IF NOT EXISTS idx_user_bot      ON users(bot_hash);

-- Import jobs table
CREATE TABLE IF NOT EXISTS import_jobs (
    id          TEXT PRIMARY KEY,
    bot_hash    TEXT NOT NULL,
    chat_id     BIGINT,
    status      TEXT DEFAULT 'pending',
    total       INTEGER DEFAULT 0,
    imported    INTEGER DEFAULT 0,
    skipped     INTEGER DEFAULT 0,
    current_chat TEXT,
    error       TEXT,
    started_at  TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);
"""


class Database:
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self, dsn: str):
        self._pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
        await self._init_schema()
        logger.info("Database pool ready")

    async def disconnect(self):
        if self._pool:
            await self._pool.close()

    async def _init_schema(self):
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA)

    # ── low-level ─────────────────────────────────────────────────────────────
    async def fetch(self, sql: str, *args) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *args)
            return [dict(r) for r in rows]

    async def fetchrow(self, sql: str, *args) -> Optional[dict]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(sql, *args)
            return dict(row) if row else None

    async def execute(self, sql: str, *args):
        async with self._pool.acquire() as conn:
            return await conn.execute(sql, *args)

    async def fetchval(self, sql: str, *args) -> Any:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(sql, *args)

    # ── bots ──────────────────────────────────────────────────────────────────
    async def get_active_bots(self) -> list[dict]:
        return await self.fetch(
            "SELECT * FROM bots WHERE is_active=TRUE ORDER BY created_at"
        )

    async def get_all_bots(self) -> list[dict]:
        return await self.fetch("SELECT * FROM bots ORDER BY created_at")

    async def get_bot(self, token_hash: str) -> Optional[dict]:
        return await self.fetchrow(
            "SELECT * FROM bots WHERE token_hash=$1", token_hash
        )

    async def upsert_bot(self, b: dict) -> dict:
        row = await self.fetchrow(
            """
            INSERT INTO bots
                (token_hash,token_encrypted,username,name,bot_id,storage_chat_id)
            VALUES ($1,$2,$3,$4,$5,$6)
            ON CONFLICT(token_hash) DO UPDATE SET
                username=EXCLUDED.username,
                name=EXCLUDED.name,
                bot_id=EXCLUDED.bot_id,
                storage_chat_id=COALESCE($6, bots.storage_chat_id),
                is_active=TRUE,
                updated_at=NOW()
            RETURNING *
            """,
            b["token_hash"], b["token_encrypted"], b.get("username"),
            b.get("name"), b.get("bot_id"), b.get("storage_chat_id"),
        )
        return dict(row)

    async def set_bot_active(self, token_hash: str, active: bool):
        await self.execute(
            "UPDATE bots SET is_active=$1, updated_at=NOW() WHERE token_hash=$2",
            active, token_hash,
        )

    async def update_bot_storage(self, token_hash: str, storage_chat_id: int):
        await self.execute(
            "UPDATE bots SET storage_chat_id=$1, updated_at=NOW() WHERE token_hash=$2",
            storage_chat_id, token_hash,
        )

    async def update_last_poll_id(self, token_hash: str, uid: int):
        await self.execute(
            "UPDATE bots SET last_poll_id=$1 WHERE token_hash=$2", uid, token_hash
        )

    async def update_telethon_session(self, token_hash: str, session_str: str):
        await self.execute(
            "UPDATE bots SET telethon_session=$1, updated_at=NOW() WHERE token_hash=$2",
            session_str, token_hash,
        )

    async def delete_bot(self, token_hash: str):
        await self.execute("DELETE FROM bots WHERE token_hash=$1", token_hash)

    # ── messages ──────────────────────────────────────────────────────────────
    async def insert_message(self, m: dict) -> bool:
        """Bot API message — dedup on update_id. Returns True if inserted."""
        try:
            raw = json.dumps(m.get("raw_json")) if m.get("raw_json") else None
            await self.execute(
                """
                INSERT INTO messages(
                    msg_id,bot_hash,update_id,kind,sender_id,sender_name,
                    chat_id,chat_title,content,caption,file_id,file_name,
                    file_size,mime_type,is_forwarded,fwd_from,reply_to_id,
                    is_edited,is_deleted,width,height,duration,
                    latitude,longitude,raw_json,source,ts
                ) VALUES (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,
                    $13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27
                ) ON CONFLICT DO NOTHING
                """,
                m.get("msg_id"), m["bot_hash"], m.get("update_id"),
                m["kind"], m.get("sender_id"), m.get("sender_name"),
                m.get("chat_id"), m.get("chat_title"),
                m.get("content"), m.get("caption"),
                m.get("file_id"), m.get("file_name"), m.get("file_size"),
                m.get("mime_type"),
                m.get("is_forwarded", False), m.get("fwd_from"),
                m.get("reply_to_id"),
                m.get("is_edited", False), m.get("is_deleted", False),
                m.get("width"), m.get("height"), m.get("duration"),
                m.get("latitude"), m.get("longitude"),
                raw, m.get("source", "bot_api"), m["ts"],
            )
            return True
        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            logger.error(f"insert_message error: {e}")
            return False

    async def message_exists(self, msg_id: int, chat_id: int,
                              bot_hash: str) -> bool:
        """Check whether a Telethon message is already in the DB."""
        val = await self.fetchval(
            "SELECT id FROM messages WHERE msg_id=$1 AND chat_id=$2 "
            "AND bot_hash=$3 AND source='telethon' LIMIT 1",
            msg_id, chat_id, bot_hash,
        )
        return val is not None

    async def insert_telethon_message(self, m: dict) -> bool:
        """MTProto message — dedup on (msg_id, chat_id, bot_hash)."""
        try:
            await self.execute(
                """
                INSERT INTO messages(
                    msg_id,bot_hash,update_id,kind,sender_id,sender_name,
                    chat_id,chat_title,content,caption,file_id,file_name,
                    file_size,mime_type,is_forwarded,fwd_from,reply_to_id,
                    is_edited,is_deleted,width,height,duration,
                    latitude,longitude,source,ts
                ) VALUES (
                    $1,$2,NULL,$3,$4,$5,$6,$7,$8,$9,$10,$11,
                    $12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,'telethon',$24
                ) ON CONFLICT DO NOTHING
                """,
                m.get("msg_id"), m["bot_hash"],
                m["kind"], m.get("sender_id"), m.get("sender_name"),
                m.get("chat_id"), m.get("chat_title"),
                m.get("content"), m.get("caption"),
                m.get("file_id"), m.get("file_name"), m.get("file_size"),
                m.get("mime_type"),
                m.get("is_forwarded", False), m.get("fwd_from"),
                m.get("reply_to_id"),
                m.get("is_edited", False), m.get("is_deleted", False),
                m.get("width"), m.get("height"), m.get("duration"),
                m.get("latitude"), m.get("longitude"), m["ts"],
            )
            return True
        except asyncpg.UniqueViolationError:
            return False
        except Exception as e:
            logger.error(f"insert_telethon_message error: {e}")
            return False

    async def update_tg_storage(self, update_id: int, bot_hash: str,
                                 storage_msg_id: int, storage_file_id: str):
        await self.execute(
            """UPDATE messages SET tg_storage_msg_id=$1, tg_storage_file_id=$2
               WHERE update_id=$3 AND bot_hash=$4""",
            storage_msg_id, storage_file_id, update_id, bot_hash,
        )

    async def get_messages(self, bot_hash: str, kind: str = None,
                           chat_id: int = None, search: str = None,
                           source: str = None,
                           limit: int = 100, before_ts: str = None) -> list[dict]:
        conds = ["bot_hash=$1"]
        params: list = [bot_hash]
        p = 2

        if kind and kind != "all":
            conds.append(f"kind=${p}"); params.append(kind); p += 1
        if chat_id:
            conds.append(f"chat_id=${p}"); params.append(chat_id); p += 1
        if search:
            q = f"%{search}%"
            conds.append(
                f"(content ILIKE ${p} OR sender_name ILIKE ${p} "
                f"OR file_name ILIKE ${p} OR caption ILIKE ${p})"
            )
            params.append(q); p += 1
        if source and source != "all":
            conds.append(f"source=${p}"); params.append(source); p += 1
        if before_ts:
            conds.append(f"ts < ${p}"); params.append(before_ts); p += 1

        where = " AND ".join(conds)
        sql = (
            f"SELECT id,msg_id,bot_hash,update_id,kind,sender_id,sender_name,"
            f"chat_id,chat_title,content,caption,file_id,file_name,file_size,"
            f"mime_type,tg_storage_msg_id,tg_storage_file_id,is_forwarded,"
            f"fwd_from,reply_to_id,is_edited,is_deleted,width,height,duration,"
            f"latitude,longitude,source,ts "
            f"FROM messages WHERE {where} "
            f"ORDER BY ts DESC LIMIT ${p}"
        )
        params.append(limit)
        rows = await self.fetch(sql, *params)
        for r in rows:
            if r.get("ts"):
                r["ts"] = r["ts"].isoformat()
        return rows

    async def get_message_stats(self, bot_hash: str) -> dict:
        total = await self.fetchval(
            "SELECT COUNT(*) FROM messages WHERE bot_hash=$1", bot_hash)
        by_kind = await self.fetch(
            "SELECT kind, COUNT(*) as n FROM messages WHERE bot_hash=$1 "
            "GROUP BY kind", bot_hash)
        by_source = await self.fetch(
            "SELECT source, COUNT(*) as n FROM messages WHERE bot_hash=$1 "
            "GROUP BY source", bot_hash)
        daily = await self.fetch(
            "SELECT DATE(ts) as day, COUNT(*) as n FROM messages "
            "WHERE bot_hash=$1 AND ts > NOW()-INTERVAL '30 days' "
            "GROUP BY day ORDER BY day", bot_hash)
        for r in daily:
            r["day"] = str(r["day"])
        return {
            "total":     total or 0,
            "by_kind":   {r["kind"]:   r["n"] for r in by_kind},
            "by_source": {r["source"]: r["n"] for r in by_source},
            "daily":     daily,
        }

    async def get_all_stats(self) -> dict:
        total  = await self.fetchval("SELECT COUNT(*) FROM messages") or 0
        texts  = await self.fetchval(
            "SELECT COUNT(*) FROM messages WHERE kind='text'") or 0
        media  = await self.fetchval(
            "SELECT COUNT(*) FROM messages "
            "WHERE kind IN ('photo','video','document','audio','voice')") or 0
        chats  = await self.fetchval("SELECT COUNT(*) FROM chats") or 0
        bots   = await self.fetchval(
            "SELECT COUNT(*) FROM bots WHERE is_active=TRUE") or 0
        mtproto = await self.fetchval(
            "SELECT COUNT(*) FROM messages WHERE source='telethon'") or 0
        return {
            "total": total, "texts": texts, "media": media,
            "chats": chats, "active_bots": bots, "mtproto_imported": mtproto,
        }

    # ── chats ─────────────────────────────────────────────────────────────────
    async def upsert_chat(self, chat_id: int, bot_hash: str,
                          type_: str, title: str, username: str = None):
        await self.execute(
            """INSERT INTO chats(chat_id,bot_hash,type,title,username,last_active)
               VALUES($1,$2,$3,$4,$5,NOW())
               ON CONFLICT(chat_id,bot_hash) DO UPDATE SET
               title=EXCLUDED.title, last_active=NOW()""",
            chat_id, bot_hash, type_, title, username,
        )

    async def get_chats(self, bot_hash: str) -> list[dict]:
        rows = await self.fetch(
            "SELECT * FROM chats WHERE bot_hash=$1 ORDER BY last_active DESC",
            bot_hash,
        )
        for r in rows:
            if r.get("last_active"):
                r["last_active"] = r["last_active"].isoformat()
            if r.get("first_seen"):
                r["first_seen"] = r["first_seen"].isoformat()
        return rows

    # ── users ─────────────────────────────────────────────────────────────────
    async def upsert_user(self, u: dict, bot_hash: str):
        await self.execute(
            """INSERT INTO users(user_id,bot_hash,first_name,last_name,username,is_bot)
               VALUES($1,$2,$3,$4,$5,$6)
               ON CONFLICT(user_id,bot_hash) DO UPDATE SET
               first_name=EXCLUDED.first_name,
               last_name=EXCLUDED.last_name,
               username=EXCLUDED.username,
               last_seen=NOW()""",
            u.get("id"), bot_hash, u.get("first_name"), u.get("last_name"),
            u.get("username"), u.get("is_bot", False),
        )

    # ── import jobs ───────────────────────────────────────────────────────────
    async def create_import_job(self, job_id: str, bot_hash: str,
                                 chat_id: Optional[int]) -> dict:
        row = await self.fetchrow(
            """INSERT INTO import_jobs(id,bot_hash,chat_id,status)
               VALUES($1,$2,$3,'pending') RETURNING *""",
            job_id, bot_hash, chat_id,
        )
        return dict(row)

    async def update_import_job(self, job_id: str, **kwargs):
        sets, vals, p = [], [], 1
        for k, v in kwargs.items():
            sets.append(f"{k}=${p}")
            vals.append(v)
            p += 1
        if not sets:
            return
        vals.append(job_id)
        await self.execute(
            f"UPDATE import_jobs SET {', '.join(sets)} WHERE id=${p}", *vals
        )

    async def get_import_job(self, job_id: str) -> Optional[dict]:
        row = await self.fetchrow(
            "SELECT * FROM import_jobs WHERE id=$1", job_id
        )
        if not row:
            return None
        r = dict(row)
        for f in ("started_at", "finished_at"):
            if r.get(f):
                r[f] = r[f].isoformat()
        return r

    async def get_import_jobs(self, bot_hash: str) -> list[dict]:
        rows = await self.fetch(
            "SELECT * FROM import_jobs WHERE bot_hash=$1 ORDER BY started_at DESC LIMIT 20",
            bot_hash,
        )
        result = []
        for r in rows:
            for f in ("started_at", "finished_at"):
                if r.get(f):
                    r[f] = r[f].isoformat()
            result.append(r)
        return result


db = Database()
